from copy import deepcopy
from collections import OrderedDict
import click
import sys
import json

from ssa import bril_to_ssa, is_ssa
from dominator_utilities import build_dominance_frontier_w_cfg
from cfg import (form_blocks, join_blocks,
                 form_cfg_w_blocks, add_unique_exit_to_cfg, reverse_cfg, join_cfg, INSTRS, SUCCS, PREDS)
from bril_core_constants import *
from bril_core_utilities import *


# ---------- MARK SWEEP DEAD CODE ELIMINATIONS -------------


def mark_sweep_dce(program):
    """
    Implementation of Mark Sweep Style DCE to remove more dead code. Meant to
    work in conjunction with SSA code.

    Can be run alongside other passes with lvn/gvn.
    """
    pass


# ---------- AGGRESSIVE DEAD CODE ELIMINATIONS -------------


UNIQUE_CFG_EXIT = "UNIQUE.EXIT"

LIVE = True
NOT_LIVE = not LIVE


def func_has_side_effects():
    pass


def function_adce(func):
    """
    From: http://www.cs.cmu.edu/afs/cs/academic/class/15745-s12/public/lectures/L14-SSA-Optimizations-1up.pdf
    Mark all instructions as Live that are:
        I/O
        Store into memory TODO: when Bril has memory instructions
        Terminator - RET
        Calls a function with side effects (e.g. most functions)
        Label
    """
    # build important auxillary data structures (READ-ONLY)
    instrs = func[INSTRS]

    cfg = form_cfg_w_blocks(func)
    entry = list(cfg.keys())[0]
    cfg_w_exit = add_unique_exit_to_cfg(cfg, UNIQUE_CFG_EXIT)
    cdg = reverse_cfg(cfg_w_exit)
    cdg[entry][PREDS].append(UNIQUE_CFG_EXIT)
    cdg[UNIQUE_CFG_EXIT][SUCCS].append(entry)
    control_dependence = build_dominance_frontier_w_cfg(cdg, UNIQUE_CFG_EXIT)

    # initialize data structures (WRITE TO)
    id2instr = OrderedDict()
    id2block = OrderedDict()
    def2id = OrderedDict()
    for block in cfg:
        for instr in cfg[block][INSTRS]:
            id2instr[id(instr)] = instr
            if DEST in instr:
                def2id[instr[DEST]] = id(instr)
            id2block[id(instr)] = block

    # initialize worklist
    marked_instrs = {id(instr): NOT_LIVE for instr in instrs}
    worklist = []
    for instr in instrs:
        if is_io(instr) or is_jmp(instr) or is_ret(instr) or is_call(instr) or is_label(instr):
            marked_instrs[id(instr)] = LIVE
            if ARGS in instr:
                for a in instr[ARGS]:
                    # add only if not an argument of the function
                    if a in def2id:
                        worklist.append(def2id[a])
            # add the control dependency parent of this instruction's block
            for cd_block in control_dependence[id2block[id(instr)]]:
                for instr in reversed(cfg[cd_block][INSTRS]):
                    if is_terminator(instr):
                        worklist.append(id(instr))

    # DO WORKLIST
    while worklist != []:
        instr_id = worklist.pop()
        if marked_instrs[instr_id] == LIVE:
            continue
        # Grab Operands of S
        marked_instrs[instr_id] = LIVE
        instr = id2instr[instr_id]
        if ARGS in instr:
            args = instr[ARGS]
            for a in args:
                # add only if not an argument of the function
                if a in def2id:
                    worklist.append(def2id[a])

        for cd_block in control_dependence[id2block[instr_id]]:
            for instr in reversed(cfg[cd_block][INSTRS]):
                if is_terminator(instr):
                    worklist.append(id(instr))

    # FINISH by keeping oive instructions
    final_instrs = []
    for instr_id in marked_instrs:
        if marked_instrs[instr_id] == LIVE:
            final_instrs.append(id2instr[instr_id])
    return final_instrs


def global_adce(program):
    """
    Aggressive Dead Code Elimination
    """
    try:
        is_ssa(program)
    except:
        program = bril_to_ssa(program)
    for func in program[FUNCTIONS]:
        new_instrs = function_adce(func)
        func[INSTRS] = new_instrs
    return program


# ---------- TRIVIAL DEAD CODE ELIMINATIONS -------------


def delete_unused_dce(program):
    """
    Delete all instructions for which a variable is assigned but never read from.
    """
    for func in program["functions"]:
        written_variables = set()
        for instr in func["instrs"]:
            if "dest" in instr:
                written_variables.add(instr["dest"])

        for instr in func["instrs"]:
            if "args" in instr:
                args = set(instr["args"])
                written_variables -= args

        new_instrs = []
        for instr in func["instrs"]:
            if "dest" in instr:
                if instr["dest"] not in written_variables:
                    new_instrs.append(instr)
            else:
                new_instrs.append(instr)

        func["instrs"] = new_instrs

    return program


def local_dce(program):
    """
    Eliminate instructions that are written over without being read, inside a
    basic block.
    """
    for func in program["functions"]:
        basic_blocks = form_blocks(func["instrs"])
        new_basic_blocks = []
        for bb in basic_blocks:
            new_bb = []
            to_delete = []
            last_use = dict()
            for idx, instr in enumerate(bb):
                if "args" in instr:
                    args = instr["args"]
                    for a in args:
                        if a in last_use:
                            (def_idx, _) = last_use[a]
                            last_use[a] = (def_idx, idx)
                if "dest" in instr:
                    dst = instr["dest"]
                    if dst in last_use:
                        (def_idx, use) = last_use[dst]
                        if use == None:
                            to_delete.append(def_idx)
                    last_use[dst] = (idx, None)

            # This is in fact incorrect! A value in one bb not used can still be used later
            # as in the diamond patter. I leave it commented out as a lesson for myself.
            # for dst, (def_idx, last_use_idx) in last_use.items():
            #     if last_use_idx == None:
            #         to_delete.append(def_idx)

            for idx, instr in enumerate(bb):
                if idx not in to_delete:
                    new_bb.append(instr)

            new_basic_blocks.append(new_bb)
        func["instrs"] = join_blocks(new_basic_blocks)
    return program


def iterate_dce(program, dce_method):
    """
    Iterates specified DCE method
    """
    has_changed = True
    while has_changed:
        old_program = deepcopy(program)
        program = dce_method(program)
        has_changed = not (program == old_program)

    return program


def dce(program, global_delete, local_delete, adce):
    """
    Naive DCE wrapper method
    """
    if bool(adce) == True:
        return global_adce(program)
    if global_delete == None and local_delete == None:
        return iterate_dce(iterate_dce(program, local_dce), delete_unused_dce)
    elif global_delete == None and local_delete:
        return iterate_dce(program, local_dce)
    elif global_delete and local_delete == None:
        return iterate_dce(program, delete_unused_dce)
    return iterate_dce(iterate_dce(program, local_dce), delete_unused_dce)


@click.command()
@click.option('--global-delete', default=1, help='Delete Globally.')
@click.option('--local-delete', default=1, help='Delete Locally.')
@click.option('--adce', default=False, help='Delete Aggressively.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(global_delete, local_delete, adce, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = dce(prog, global_delete, local_delete, adce)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
