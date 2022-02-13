import sys
import json
import click
from copy import deepcopy


from cfg import form_cfg, form_blocks, form_block_dict
from bril_core_constants import *
from worklist_solver import Worklist


NOT_CONSTANT = "?"
UNDEFINED = "!"


def interpret_expr(expr, ctx):
    assert type(expr) == dict
    assert type(ctx) == dict
    if OP in expr and expr[OP] == CONST:
        return expr[VALUE]
    elif OP in expr and expr[OP] == ID:
        var = expr[ARGS][0]
        return ctx[var]
    elif OP in expr and expr[OP] in BRIL_BINOPS:
        op = expr[OP]
        args = expr[ARGS]
        assert len(args) == 2
        arg1 = args[0]
        arg2 = args[1]
        if op == ADD:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] + ctx[arg2]
        elif op == SUB:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] - ctx[arg2]
        elif op == MUL:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] * ctx[arg2]
        elif op == DIV:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] // ctx[arg2]
        elif op == EQ:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] == ctx[arg2]
        elif op == LE:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] <= ctx[arg2]
        elif op == GE:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] >= ctx[arg2]
        elif op == LT:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] < ctx[arg2]
        elif op == GT:
            assert type(ctx[arg1]) == int and type(ctx[arg2]) == int
            return ctx[arg1] > ctx[arg2]
        elif op == AND:
            assert type(ctx[arg1]) == bool and type(ctx[arg2]) == bool
            return ctx[arg1] and ctx[arg2]
        elif op == OR:
            assert type(ctx[arg1]) == bool and type(ctx[arg2]) == bool
            return ctx[arg1] or ctx[arg2]
        else:
            raise RuntimeError(
                f"Unmatched binary operator {op} while interpreting {expr}.")
    elif OP in expr and expr[OP] in BRIL_UNOPS:
        op = expr[OP]
        args = expr[ARGS]
        assert len(args) == 1
        arg1 = args[0]
        if op == NOT:
            assert type(ctx[arg1]) == bool
            return not ctx[arg1]
        else:
            raise RuntimeError(
                f"Unmatched unary operator {op} while interpreting {expr}.")
    raise RuntimeError(f"Cannot interpret {expr} under context {ctx}.")


def transfer(in_block, block):
    assert type(in_block) == dict
    assert type(block) == list
    variables = deepcopy(in_block)
    for instr in block:
        if DEST in instr:
            var = instr[DEST]
            # call type, we choose not to interpret (TODO: add interpret for calls)
            if FUNCS in instr:
                variables[var] = NOT_CONSTANT
            elif ARGS in instr:
                args = instr[ARGS]
                constant = True
                for a in args:
                    if a not in variables:
                        variables[a] = UNDEFINED
                        constant = False
                        break
                    val_type = variables[a]
                    if val_type == NOT_CONSTANT:
                        constant = False
                        break
                    elif val_type == UNDEFINED:
                        constant = False
                        break
                # do interpretation
                if constant:
                    try:
                        result = interpret_expr(instr, variables)
                    except:
                        result = NOT_CONSTANT
                    variables[var] = result
                else:
                    variables[var] = NOT_CONSTANT
            # const type instruction
            elif VALUE in instr:
                variables[var] = instr[VALUE]
            # other assignment instruction that is unhandled
            else:
                raise RuntimeError(f"{instr} should contain args.")
    return variables


def merge(blocks):
    variables = dict()
    for b in blocks:
        for var, val in b.items():
            if var in variables:
                # allow for variables that hold same constant over branches
                if variables[var] == val:
                    variables[var] = val
                else:
                    variables[var] = NOT_CONSTANT
            else:
                variables[var] = val
    return variables


def constant_prop_func(function):
    cfg = form_cfg(function)
    assert len(cfg) != 0
    entry = list(cfg.items())[0][0]
    blocks = form_block_dict(form_blocks(function["instrs"]))
    init = dict()
    if ARGS in function:
        args = function[ARGS]
        for a in args:
            init[a[NAME]] = NOT_CONSTANT
    worklist = Worklist(entry, cfg, blocks, init, merge, transfer)
    return worklist.solve()


def constant_prop(program):
    for func in program["functions"]:
        (in_dict, out_dict) = constant_prop_func(func)
        print(f"Function: {func[NAME]}")
        print(f"In:")
        for (k, v) in in_dict.items():
            if v == {}:
                print(f"\t{k}: No Constant Definitions.")
            else:
                for (var, val) in v.items():
                    print(f"\t{k}: {var} has value {val}.")
        print(f"Out:")
        for (k, v) in out_dict.items():
            if v == {}:
                print(f"\t{k}: No Constant Definitions.")
            else:
                for (var, val) in v.items():
                    print(f"\t{k}: {var} has value {val}.")
    return


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    constant_prop(prog)


if __name__ == "__main__":
    main()
