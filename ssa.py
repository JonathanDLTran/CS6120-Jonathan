from ntpath import join
import click
import sys
import json

from numpy import s_

from bril_core_constants import *
from cfg import SUCCS, TERMINATORS, form_cfg_succs_preds, form_blocks, form_block_dict, join_blocks
from dominator_utilities import build_dominance_tree


def gen_var_name():
    pass


def insert_at_end_of_bb(block, instr):
    if len(block) == 0:
        block.append(instr)
        return
    last_instr = block[-1]
    if OP in last_instr and last_instr[OP] in TERMINATORS:
        block.insert(-1, instr)
        return
    else:
        block.append(instr)
        return


def func_from_ssa(func):
    assert type(func) == list
    block_dict = form_block_dict(form_blocks(func))
    for block_name, instrs in block_dict.items():
        new_instrs = []
        for instr in instrs:
            if OP in instr and instr[OP] == PHI:
                dst = instr[DEST]
                args = instr[ARGS]
                typ = instr[TYPE]
                labels = instr[LABELS]
                for a, l in zip(args, labels):
                    prev_block = block_dict[l]
                    new_instr = {OP: ID, TYPE: typ, ARGS: [a], DEST: dst}
                    insert_at_end_of_bb(prev_block, new_instr)
            else:
                new_instrs.append(instr)
            block_dict[block_name] = new_instrs
    return join_blocks([block_dict[block_name] for block_name in block_dict])


def ssa_to_bril(program):
    for func in program["functions"]:
        new_func_instrs = func_from_ssa(func["instrs"])
        func["instrs"] = new_func_instrs
    return program


def insert_phi(func):
    pass


def rename(block_map, block_name, stack, cfg, dom_tree):
    pushed_names = dict()

    block = block_map[block_name]
    for instr in block:
        if ARGS in instr:
            old_args = instr[ARGS]
            new_args = []
            for old in old_args:
                (v, i) = stack[old]
                var = f"{v}_{i}"
                new_args.append(var)
            instr[ARGS] = new_args
        if DEST in instr:
            dst = instr[DEST]
            (v, i) = stack[dst]
            new_name = f"{v}_{i + 1}"
            instr[DEST] = new_name
            stack[dst].append((v, i + 1))

            if dst in pushed_names:
                pushed_names[dst].append(new_name)
            else:
                pushed_names[dst] = [new_name]

    for s in cfg[block][SUCCS]:
        s_phi_nodes = []
        for instr in s:
            if OP in instr and instr[OP] == PHI:
                s_phi_nodes.append(instr)
        for p in s_phi_nodes:
            p_args = p[ARGS]
            new_p_args = []
            for a in p_args:
                if a in stack:
                    (v, i) = stack[a]
                    new_var = f"{v}_{i}"
                    new_p_args.append(new_var)
                else:
                    new_p_args.append(a)
            p[ARGS] = new_p_args

    for new_block_name in dom_tree[block_name]:
        rename(block_map, new_block_name, stack, cfg, dom_tree)

    for var, new_names in pushed_names.items():
        while new_names != []:
            _ = new_names.pop()
            stack[var].pop()


def func_to_ssa(func):
    assert type(func) == list


def bril_to_ssa(program):
    for func in program["functions"]:
        new_func_instrs = func_to_ssa(func["instrs"])
        func["instrs"] = new_func_instrs
    return is_ssa(program)


def is_ssa(program):
    for func in program["functions"]:
        def_vars = set()
        if ARGS in func:
            for a in func[ARGS]:
                def_vars.add(a)
        for instr in func["instrs"]:
            if DEST in instr:
                dst = instr[DEST]
                if dst in def_vars:
                    raise RuntimeError(f"Program is not in SSA form.")
                def_vars.add(dst)
    return program


@click.command()
@click.option('--to-ssa', default=False, help='Converts Bril program to SSA from.')
@click.option('--from-ssa', default=False, help='Converts Bril program out of SSA form.')
@click.option('--pretty-print', default=False, help='Print transformed program.')
def main(to_ssa, from_ssa, pretty_print):
    prog = json.load(sys.stdin)
    if to_ssa:
        prog = bril_to_ssa(prog)
    if from_ssa:
        prog = ssa_to_bril(prog)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
