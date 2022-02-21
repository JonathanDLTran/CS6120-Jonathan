from copy import deepcopy
import click
import sys
import json
from collections import defaultdict

from bril_core_constants import *
from bril_core_utilities import *
from cfg import PREDS, SUCCS, TERMINATORS, form_cfg_succs_preds, form_blocks, form_block_dict, join_blocks_w_labels
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
    return join_blocks_w_labels(block_dict)


def ssa_to_bril(program):
    for func in program["functions"]:
        new_func_instrs = func_from_ssa(func["instrs"])
        func["instrs"] = new_func_instrs
    return is_not_ssa(program)


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


def gen_new_var(var, var_to_fresh_index):
    if var not in var_to_fresh_index:
        var_to_fresh_index[var] = 0
    new_name = f"{var}_{var_to_fresh_index[var] + 1}"
    var_to_fresh_index[var] += 1
    return new_name


def is_ssa_var(var):
    return "_" in var and (var[var.rindex("_") + 1:]).isnumeric()


def insert_into_new_branch(block_dict, succ_name, cfg, var_to_fresh_index, a, i, phi_node):
    pred_block_name = cfg[succ_name][PREDS][i]
    new_var = f"{a}_{var_to_fresh_index[a] + 1}"
    var_to_fresh_index[a] += 1
    new_instr_type = phi_node[TYPE]
    if new_instr_type == BOOL:
        new_instr = {OP: CONST,
                     VALUE: True, DEST: new_var, TYPE: BOOL}
    elif new_instr_type == INT:
        new_instr = {OP: CONST,
                     VALUE: 0, DEST: new_var, TYPE: INT}
    else:
        raise RuntimeError(
            f"Unhandled type {new_instr_type}.")
    insert_at_end_of_bb(
        block_dict[pred_block_name], new_instr)

    return new_var


def rename(block_dict, block_name, stack, cfg, dom_tree, var_to_fresh_index):
    pushed_names = defaultdict(list)

    block = block_dict[block_name]
    for instr in block:
        if not is_phi(instr) and ARGS in instr:
            old_args = instr[ARGS]
            new_args = []
            for old in old_args:
                var = stack[old][-1]
                new_args.append(var)
            instr[ARGS] = new_args

        if DEST in instr:
            dst = instr[DEST]
            new_name = gen_new_var(dst, var_to_fresh_index)
            instr[DEST] = new_name
            stack[dst].append(new_name)
            pushed_names[dst].append(new_name)

    for succ_name in cfg[block_name][SUCCS]:
        succ_phi_nodes = []
        for instr in block_dict[succ_name]:
            if OP in instr and instr[OP] == PHI:
                succ_phi_nodes.append(instr)

        for phi_node in succ_phi_nodes:
            p_args = phi_node[ARGS]
            p_labels = phi_node[LABELS]
            if block_name not in p_labels:
                raise RuntimeError(
                    f"Block name {block_name} is not in the labels of phi node {phi_node} in basic block {succ_name}.")

            label_index = p_labels.index(block_name)
            new_p_args = []
            for i, a in enumerate(p_args):
                if i != label_index:
                    new_p_args.append(a)
                    continue
                # a was defined before
                if a in stack:
                    # if stack[a] is empty, a is not defined along a certain branch
                    if stack[a] == []:
                        new_var = insert_into_new_branch(
                            block_dict, succ_name, cfg, var_to_fresh_index, a, i, phi_node)
                    else:
                        new_var = stack[a][-1]
                elif is_ssa_var(a):
                    new_var = a
                # a was never defined before, we add a new branch
                else:
                    var_to_fresh_index[a] = 0
                    new_var = insert_into_new_branch(
                        block_dict, succ_name, cfg, var_to_fresh_index, a, i, phi_node)

                new_p_args.append(new_var)
            phi_node[ARGS] = new_p_args

    for new_block_name in dom_tree[block_name]:
        rename(block_dict, new_block_name, stack,
               cfg, dom_tree, var_to_fresh_index)

    for var, new_names in pushed_names.items():
        while new_names != []:
            new_names.pop()
            stack[var].pop()


def rename_old(block_dict, block_name, stack, cfg, dom_tree, var_to_fresh_index):
    pushed_names = defaultdict(list)

    block = block_dict[block_name]
    for instr in block:
        if ARGS in instr:
            old_args = instr[ARGS]
            new_args = []
            for old in old_args:
                if not is_phi(instr):
                    var = stack[old][-1]
                    new_args.append(var)
                elif old not in stack and is_phi(instr):
                    new_args.append(old)
                else:
                    # was not successor block replaced, have to go back a few blocks.
                    var = stack[old][-1]
                    new_args.append(var)
            instr[ARGS] = new_args
        if DEST in instr:
            dst = instr[DEST]

            if dst not in var_to_fresh_index:
                var_to_fresh_index[dst] = 0

            new_name = f"{dst}_{var_to_fresh_index[dst] + 1}"
            var_to_fresh_index[dst] += 1

            instr[DEST] = new_name
            stack[dst].append(new_name)

            pushed_names[dst].append(new_name)

    for succ_name in cfg[block_name][SUCCS]:
        s_phi_nodes = []
        for instr in block_dict[succ_name]:
            if OP in instr and instr[OP] == PHI:
                s_phi_nodes.append(instr)
        for p in s_phi_nodes:
            p_args = p[ARGS]
            p_labels = p[LABELS]
            if block_name in p_labels:
                label_index = p_labels.index(block_name)
                new_p_args = []
                for i, a in enumerate(p_args):
                    if i == label_index:
                        if a in stack:
                            # if stack[a] is empty, a is not defined along a certain branch
                            # to fix, we insert a pseudo-unused instruction
                            # at least according to the user, who expects
                            # that branch never to have a used
                            if stack[a] == []:
                                pred_block_name = cfg[succ_name][PREDS][i]
                                new_var = f"{a}_{var_to_fresh_index[a] + 1}"
                                var_to_fresh_index[a] += 1
                                new_instr_type = p[TYPE]
                                if new_instr_type == BOOL:
                                    new_instr = {OP: CONST,
                                                 VALUE: True, DEST: new_var, TYPE: BOOL}
                                elif new_instr_type == INT:
                                    new_instr = {OP: CONST,
                                                 VALUE: 0, DEST: new_var, TYPE: INT}
                                else:
                                    raise RuntimeError(
                                        f"Unhandled type {new_instr_type}.")
                                insert_at_end_of_bb(
                                    block_dict[pred_block_name], new_instr)
                            else:
                                new_var = stack[a][-1]
                        elif "_" in a and (a[a.rindex("_") + 1:]).isnumeric():
                            new_var = a
                        else:
                            pred_block_name = cfg[succ_name][PREDS][i]
                            var_to_fresh_index[a] = 0
                            new_var = f"{a}_{var_to_fresh_index[a] + 1}"
                            var_to_fresh_index[a] += 1
                            new_instr_type = p[TYPE]
                            if new_instr_type == BOOL:
                                new_instr = {OP: CONST,
                                             VALUE: True, DEST: new_var, TYPE: BOOL}
                            elif new_instr_type == INT:
                                new_instr = {OP: CONST,
                                             VALUE: 0, DEST: new_var, TYPE: INT}
                            else:
                                raise RuntimeError(
                                    f"Unhandled type {new_instr_type}.")
                            insert_at_end_of_bb(
                                block_dict[pred_block_name], new_instr)

                        new_p_args.append(new_var)
                    else:
                        new_p_args.append(a)
                p[ARGS] = new_p_args
            else:
                raise RuntimeError(
                    f"Block name {block_name} is not in the labels of phi node {p} in basic block {succ_name}.")

    for new_block_name in dom_tree[block_name]:
        rename_old(block_dict, new_block_name, stack,
                   cfg, dom_tree, var_to_fresh_index)

    for var, new_names in pushed_names.items():
        while new_names != []:
            _ = new_names.pop()
            stack[var].pop()


def func_to_ssa(func):
    cfg = form_cfg_succs_preds(func["instrs"])
    block_dict = form_block_dict(form_blocks(func["instrs"]))
    dom_tree, _ = build_dominance_tree(func)
    dom_frontier = build_dominance_frontier(func)
    entry = list(block_dict.keys())[0]

    insert_phi(func, dom_frontier, cfg, block_dict, entry)

    # set up stack with arguments as needed
    stack = defaultdict(list)
    var_to_fresh_index = {}
    if ARGS in func:
        new_args = []
        for a in func[ARGS]:
            new_arg_name = f"{a[NAME]}_1"
            stack[a[NAME]] = [new_arg_name]
            var_to_fresh_index[a[NAME]] = 1
            new_arg = deepcopy(a)
            new_arg[NAME] = new_arg_name
            new_args.append(new_arg)
        func[ARGS] = new_args

    rename(block_dict, entry, stack, cfg, dom_tree, var_to_fresh_index)

    return join_blocks_w_labels(block_dict)


def bril_to_ssa(program):
    for func in program["functions"]:
        new_instrs = func_to_ssa(func)
        func["instrs"] = new_instrs
    return is_ssa(program)


def is_ssa(program):
    for func in program["functions"]:
        def_vars = set()
        if ARGS in func:
            for a in func[ARGS]:
                def_vars.add(a[NAME])
        for instr in func["instrs"]:
            if DEST in instr:
                dst = instr[DEST]
                if dst in def_vars:
                    raise RuntimeError(f"Program is not in SSA form.")
                def_vars.add(dst)
    return program


def is_not_ssa(program):
    for func in program["functions"]:
        for instr in func["instrs"]:
            if OP in instr and instr[OP] == PHI:
                raise RuntimeError(
                    f"Program is still in SSA form: contains phi at {instr}.")
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
