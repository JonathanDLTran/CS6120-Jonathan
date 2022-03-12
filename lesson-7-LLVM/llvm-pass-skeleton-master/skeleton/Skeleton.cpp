#include "llvm/ADT/Statistic.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/LegacyPassManager.h"
#include "llvm/IR/Module.h"
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

bool SkeletonPass::runOnModule(Module &M) {
    errs() << "In module called: " << M.getName() << "!\n";

    for (auto &F : M) {
        errs() << F << "\n";

        for (auto &B : F) {
            errs() << B << "\n";

            for (auto &I : B) {
                errs() << I << "\n";
            }
        }
    }

    return false;
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