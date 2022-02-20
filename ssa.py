import click
import sys
import json
from collections import defaultdict

from bril_core_constants import *
from cfg import PREDS, SUCCS, TERMINATORS, form_cfg_succs_preds, form_blocks, form_block_dict, join_blocks
from dominator_utilities import build_dominance_tree, build_dominance_frontier


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


def insert_at_front_of_bb(block, instr):
    if len(block) == 0:
        block.append(instr)
        return
    first_instr = block[0]
    if LABEL in first_instr:
        block.insert(1, instr)
        return
    else:
        block.insert(0, instr)
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


def insert_phi(func, df, cfg, block_dict, entry):
    assert type(func) == dict

    variables = defaultdict(list)
    var_types = dict()
    if ARGS in func:
        args = func[ARGS]
        for a in args:
            variables[a[NAME]].append(entry)
            var_types[a[NAME]] = a[TYPE]

    for block, instrs in block_dict.items():
        for instr in instrs:
            if DEST in instr:
                dst = instr[DEST]
                variables[dst].append(block)
                var_types[dst] = instr[TYPE]
            if ARGS in instr:
                args = instr[ARGS]
                for a in args:
                    if a not in variables:
                        raise RuntimeError(
                            f"SSA: INSERT PHI: Undefined variable {a} used in {instr}.")

    for v in variables:
        added_blocks = set()
        for defined_block in variables[v]:
            for df_block in df[defined_block]:
                if df_block not in added_blocks:
                    args = []
                    preds = cfg[df_block][PREDS]
                    for _ in range(len(preds)):
                        args.append(v)
                    phi = {OP: PHI, TYPE: var_types[v],
                           LABELS: preds,  ARGS: args, DEST: v}
                    insert_at_front_of_bb(block_dict[df_block], phi)
                    added_blocks.add(df_block)
                if df_block not in variables[v]:
                    variables[v].append(df_block)


def rename(block_dict, block_name, stack, cfg, dom_tree, var_to_fresh_index):
    pushed_names = dict()

    block = block_dict[block_name]
    for instr in block:
        if ARGS in instr:
            old_args = instr[ARGS]
            new_args = []
            for old in old_args:
                (v, i) = stack[old][-1]
                var = f"{v}_{i}"
                new_args.append(var)
            instr[ARGS] = new_args
        if DEST in instr:
            dst = instr[DEST]
            if dst in stack:
                (v, i) = stack[dst][-1]
            else:
                (v, i) = (dst, 0)
            new_name = f"{v}_{i + 1}"
            instr[DEST] = new_name
            stack[dst].append((v, i + 1))

            if dst in pushed_names:
                pushed_names[dst].append(new_name)
            else:
                pushed_names[dst] = [new_name]

    for s in cfg[block_name][SUCCS]:
        s_phi_nodes = []
        for instr in s:
            if OP in instr and instr[OP] == PHI:
                s_phi_nodes.append(instr)
        for p in s_phi_nodes:
            p_args = p[ARGS]
            new_p_args = []
            for a in p_args:
                if a in stack:
                    (v, i) = stack[a][-1]
                    new_var = f"{v}_{i}"
                    new_p_args.append(new_var)
                else:
                    new_p_args.append(a)
            p[ARGS] = new_p_args

    for new_block_name in dom_tree[block_name]:
        rename(block_dict, new_block_name, stack, cfg, dom_tree)

    for var, new_names in pushed_names.items():
        while new_names != []:
            _ = new_names.pop()
            stack[var].pop()


def func_to_ssa(func):
    # set up stack with arguments as needed
    stack = defaultdict(list)
    if ARGS in func:
        new_args = []
        for a in func[ARGS]:
            stack[a].append((a, 0))
            new_args.append(f"{a}_0")
        func[ARGS] = new_args

    cfg = form_cfg_succs_preds(func["instrs"])
    block_dict = form_block_dict(form_blocks(func["instrs"]))
    dom_tree, _ = build_dominance_tree(func)
    dom_frontier = build_dominance_frontier(func)
    entry = list(block_dict.keys())[0]

    insert_phi(func, dom_frontier, cfg, block_dict, entry)

    rename(block_dict, entry, stack, cfg, dom_tree)

    return join_blocks([block_dict[key] for key in block_dict])


def bril_to_ssa(program):
    for func in program["functions"]:
        new_instrs = func_to_ssa(func)
        func["instrs"] = new_instrs
    return program
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
