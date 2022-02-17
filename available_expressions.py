import sys
import json
import click
from copy import deepcopy
from collections import OrderedDict

from cfg import form_cfg, form_blocks, form_block_dict
from bril_core_constants import *
from worklist_solver import Worklist


AVAILABLE_GENERATORS = [
    ADD, SUB, MUL, DIV,
    LE, GE, LT, GT, EQ,
    NOT, AND, OR
]


def instr_to_expr(instr):
    assert type(instr) == dict
    if OP in instr:
        op = instr[OP]
        if op in AVAILABLE_GENERATORS:
            return tuple([op, *instr[ARGS]])
    raise RuntimeError(f"Cannot Convert Instr {instr} to tuple expression.")


def expr_to_str(expr):
    assert type(expr) == tuple
    assert len(expr) >= 2
    op = expr[0]
    if op == ADD:
        return f"({expr[1]} + {expr[2]})"
    elif op == SUB:
        return f"({expr[1]} - {expr[2]})"
    elif op == MUL:
        return f"({expr[1]} * {expr[2]})"
    elif op == DIV:
        return f"({expr[1]} // {expr[2]})"
    elif op == EQ:
        return f"({expr[1]} == {expr[2]})"
    elif op == LE:
        return f"({expr[1]} <= {expr[2]})"
    elif op == GE:
        return f"({expr[1]} >= {expr[2]})"
    elif op == LT:
        return f"({expr[1]} < {expr[2]})"
    elif op == GT:
        return f"({expr[1]} > {expr[2]})"
    elif op == NOT:
        return f"(not {expr[1]})"
    elif op == AND:
        return f"({expr[1]} && {expr[2]})"
    elif op == OR:
        return f"({expr[1]} || {expr[2]})"
    raise RuntimeError(f"Cannot Handle Conversion of {expr} to String.")


def kills(instr):
    assert type(instr) == dict
    kills = set()
    if DEST in instr:
        kills.add(instr[DEST])
    return kills


def gens(instr):
    assert type(instr) == dict
    gens = set()
    if OP in instr and instr[OP] in AVAILABLE_GENERATORS:
        available_expr = instr_to_expr(instr)
        gens.add(available_expr)
    return gens


def diff(union, kills):
    assert type(union) == set
    assert type(kills) == set
    out = set()
    for expr in union:
        args = expr[1:]
        add_expr = True
        for k in kills:
            if k in args:
                add_expr = False
        if add_expr:
            out.add(expr)
    return out


def transfer(in_block, block):
    assert type(in_block) == set
    assert type(block) == list
    intermediate = deepcopy(in_block)
    for instr_pair in block:
        intermediate = diff(intermediate.union(
            gens(instr_pair)), kills(instr_pair))
    return intermediate


def merge(blocks):
    assert type(blocks) == list
    if len(blocks) == 0:
        return set()
    merged = set(blocks[0])
    for b in blocks:
        merged = merged.intersection(set(b))
    return merged


def available_exprs_func(function):
    cfg = form_cfg(function)
    assert len(cfg) != 0
    entry = list(cfg.items())[0][0]
    blocks = form_block_dict(form_blocks(function["instrs"]))
    init = set()
    worklist = Worklist(entry, cfg, blocks, init, merge, transfer)
    return worklist.solve()


def available_exprs(program):
    for func in program["functions"]:
        (in_dict, out_dict) = available_exprs_func(func)

        final_in_dict = OrderedDict()
        for (key, inner_set) in in_dict.items():
            inner_lst = sorted(list(inner_set))
            final_in_dict[key] = inner_lst
        final_out_dict = OrderedDict()
        for (key, inner_set) in out_dict.items():
            inner_lst = sorted(list(inner_set))
            final_out_dict[key] = inner_lst

        print(f"Function: {func[NAME]}")
        print(f"In:")
        for (k, v) in final_in_dict.items():
            if v == []:
                print(f"\t{k}: No Available Expressions.")
            else:
                for expr in v:
                    print(
                        f"\t{k}: {expr_to_str(expr)} is available.")
        print(f"Out:")
        for (k, v) in final_out_dict.items():
            if v == []:
                print(f"\t{k}: No Available Expressions.")
            else:
                for expr in v:
                    print(
                        f"\t{k}: {expr_to_str(expr)} is available.")
    return


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    available_exprs(prog)


if __name__ == "__main__":
    main()
