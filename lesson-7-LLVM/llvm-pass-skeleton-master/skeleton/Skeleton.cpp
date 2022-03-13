#include <map>
#include <tuple>
#include <vector>

#include "llvm/ADT/Statistic.h"
#include "llvm/IR/Argument.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/User.h"
#include "llvm/Support/Debug.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Transforms/IPO/PassManagerBuilder.h"

using namespace llvm;

/**
 * The below code is from:
 * https://stackoverflow.com/questions/36208942/usage-of-functionpass-over-modulepass-when-creating-llvm-passes
 * and https://github.com/sampsyo/llvm-pass-skeleton/issues/7
 *
 * I faced the same issue with hjow to set up a Module Pass, and evewntually
 * stumbled on this Stackoverflow post which forwarded me back to Professor
 * Sampson's page, but this time to a github issue #7 for module passes
 *
 * The overall structure uses the solution that ghost suggests, by changing the
 * EP pass order
 */
namespace {
struct SkeletonPass : public ModulePass {
    static char ID;
    SkeletonPass() : ModulePass(ID) {}

    virtual bool runOnModule(Module &M) override;
};
}  // namespace

char SkeletonPass::ID = 0;

const std::string MAIN_FUNCTION_NAME = "main";

bool func_has_subcalls_or_more_than_one_ret(Function &F) {
    int num_rets = 0;
    int num_basic_blocks = 0;
    for (auto &B : F) {
        ++num_basic_blocks;
        for (auto &I : B) {
            if (auto *op = dyn_cast<CallInst>(&I)) {
                return false;
            }
            if (auto *op = dyn_cast<ReturnInst>(&I)) {
                ++num_rets;
            }
        }
    }
    return num_rets == 1 && num_basic_blocks == 1;
}

StringRef get_function_name(CallInst *call) {
    /**
     * This function is from:
     * https://stackoverflow.com/questions/11686951/how-can-i-get-function-name-from-callinst-in-llvm
     */
    Function *fun = call->getCalledFunction();
    if (fun)                    // thanks @Anton Korobeynikov
        return fun->getName();  // inherited from llvm::Value
    else
        return StringRef("indirect call");
}

std::vector<Instruction *> get_function_instructions(llvm::StringRef func_name,
                                                     Module &M) {
    std::vector<Instruction *> func_instrs;
    for (auto &F : M) {
        if (F.getName() == func_name) {
            for (auto &B : F) {
                for (auto &I : B) {
                    func_instrs.push_back(&I);
                }
            }
        }
    }
    return func_instrs;
}

bool SkeletonPass::runOnModule(Module &M) {
    /**
     * We attempt to inline as much as we can into main
     *
     * First, we mark each function f that is not main true/false whether
     * it calls other functions or not. This controls whether f can be inlined
     * into main.
     *
     * Second, we walk the main function, and check for call instructions
     *
     * Third, at each call instruction, if the call is to a function that has no
     * subcalls, we copy the arguments. We then insert the code for that
     * function.
     */
    std::map<llvm::StringRef, bool> func_call_map;
    std::map<StringRef, std::vector<Value *>> func_to_arguments;
    std::map<StringRef, std::vector<Value *>> func_to_parameters;
    for (auto &F : M) {
        bool has_subcalls = func_has_subcalls_or_more_than_one_ret(F);
        StringRef func_name = F.getName();
        func_call_map[func_name] = has_subcalls;
        std::vector<Value *> arguments;
        for (auto it = F.arg_begin(); it != F.arg_end(); ++it) {
            Value *arg = it;
            arguments.push_back(arg);
        }
        func_to_arguments[func_name] = arguments;
    }

    for (auto &F : M) {
        if (F.getName() == MAIN_FUNCTION_NAME) {
            std::vector<std::tuple<std::vector<Instruction *>, Instruction *,
                                   StringRef>>
                call_triples;
            std::vector<Instruction *> delete_instrs;
            for (auto &B : F) {
                for (auto &I : B) {
                    if (auto *op = dyn_cast<CallInst>(&I)) {
                        llvm::StringRef func_name = get_function_name(op);
                        auto search = func_call_map.find(func_name);
                        if (search != func_call_map.end() && search->second) {
                            std::vector<Instruction *> func_instrs =
                                get_function_instructions(func_name, M);
                            std::tuple<std::vector<Instruction *>,
                                       Instruction *, StringRef>
                                triple =
                                    std::make_tuple(func_instrs, &I, func_name);
                            call_triples.push_back(triple);
                            delete_instrs.push_back(&I);

                            std::vector<Value *> parameters;
                            for (auto it = op->arg_begin(); it != op->arg_end();
                                 ++it) {
                                Use *param = it;
                                Value *param_val = dyn_cast<Value>(param);
                                parameters.push_back(param_val);
                            }
                            func_to_parameters[func_name] = parameters;
                        }
                    }
                }
            }

            for (auto triple : call_triples) {
                std::vector<Instruction *> func_instrs = std::get<0>(triple);
                Instruction *call_instr = std::get<1>(triple);
                StringRef func_name = std::get<2>(triple);

                IRBuilder<> builder(call_instr);
                std::map<Value *, Value *> old_to_new_map;
                for (Instruction *func_instr : func_instrs) {
                    if (!func_instr->isTerminator()) {
                        Instruction *cloned_instr = func_instr->clone();
                        Value *val = dyn_cast<Value>(cloned_instr);
                        User *val_use = dyn_cast<User>(val);
                        for (int i = 0; i < val_use->getNumOperands(); i++) {
                            Value *operand = val_use->getOperand(i);
                            auto search = old_to_new_map.find(operand);
                            if (search != old_to_new_map.end()) {
                                Value *new_operand = search->second;
                                val_use->setOperand(i, new_operand);
                            } else if (isa<Argument>(operand)) {
                                for (int j = 0;
                                     j < func_to_arguments[func_name].size();
                                     j++) {
                                    Value *arg =
                                        func_to_arguments[func_name][j];
                                    Value *param =
                                        func_to_parameters[func_name][j];
                                    if (operand == arg) {
                                        val_use->setOperand(i, param);
                                    }
                                }
                            }
                        }
                        Value *inserted_val = builder.Insert(val);
                        Value *original_val = dyn_cast<Value>(func_instr);
                        old_to_new_map[original_val] = inserted_val;
                    } else if (isa<ReturnInst>(func_instr)) {
                        for (auto &U : call_instr->uses()) {
                            User *user = U.getUser();
                            User *ret_use = dyn_cast<User>(func_instr);
                            Value *ret_operand = ret_use->getOperand(0);
                            auto search = old_to_new_map.find(ret_operand);
                            if (search != old_to_new_map.end()) {
                                user->setOperand(U.getOperandNo(),
                                                 search->second);
                            } else {
                                throw "Expected argument of ret to have been processed already!";
                            }
                        }
                    } else {
                        throw "Expected only 1 terminator, and must be "
                                  "ret!";
                    }
                }
            }

            std::reverse(delete_instrs.begin(), delete_instrs.end());
            for (auto *instr : delete_instrs) {
                *instr->eraseFromParent();
            }
        }
    }

    return true;
}

// Automatically enable the pass.
// http://adriansampson.net/blog/clangpass.html
static void registerSkeletonPass(const PassManagerBuilder &,
                                 legacy::PassManagerBase &PM) {
    PM.add(new SkeletonPass());
}

static RegisterStandardPasses RegisterMyPass(
    PassManagerBuilder::EP_ModuleOptimizerEarly, registerSkeletonPass);

static RegisterStandardPasses RegisterMyPass0(
    PassManagerBuilder::EP_EnabledOnOptLevel0, registerSkeletonPass);