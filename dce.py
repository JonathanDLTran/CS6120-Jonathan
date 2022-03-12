from copy import deepcopy
from collections import OrderedDict
import click
import sys
import json

from ssa import bril_to_ssa, is_ssa
from dominator_utilities import build_dominance_frontier_w_cfg, get_backedges_w_cfg, get_dominators_w_cfg
from cfg import (form_blocks, join_blocks,
                 form_cfg_w_blocks, add_unique_exit_to_cfg, reverse_cfg, INSTRS, SUCCS, PREDS)
from bril_core_constants import *
from bril_core_utilities import *


# ---------- MARK SWEEP DEAD CODE ELIMINATIONS -------------


MARKED = True
NOT_MARKED = not MARKED


def is_critical(instr):
    return is_io(instr) or is_call(instr) or is_ret(instr)


def function_mark_sweep(func):
    """
    ASSUMES SSA FORM
    https://yunmingzhang.files.wordpress.com/2013/12/dcereport-2.pdf
    """
    # set up data structures
    cfg = form_cfg_w_blocks(func)
    cfg_w_exit = add_unique_exit_to_cfg(cfg, UNIQUE_CFG_EXIT)
    cdg = reverse_cfg(cfg_w_exit)
    post_dominators = get_dominators_w_cfg(func, UNIQUE_CFG_EXIT)
    reverse_dominance_frontier = build_dominance_frontier_w_cfg(
        cdg, UNIQUE_CFG_EXIT)

    # initialize
    id2instr = dict()
    id2block = dict()
    id2mark = dict()
    def2id = dict()
    useful_blocks = set()
    worklist = []
    for block in cfg:
        for instr in cfg[block][INSTRS]:
            instr_id = id(instr)
            if is_critical(instr):
                worklist.append(instr_id)
                id2mark[instr_id] = MARKED
                useful_blocks.add(block)
            else:
                id2mark[instr_id] = NOT_MARKED
            if DEST in instr:
                def2id[instr[DEST]] = instr_id
            id2instr[instr_id] = instr
            id2block[instr_id] = block

    # mark phase
    while worklist != []:
        current_inst_id = worklist.pop()
        current_inst = id2instr[current_inst_id]
        if ARGS in current_inst:
            for defining in current_inst[ARGS]:
                if id2mark[def_id] == NOT_MARKED:
                    def_id = def2id[defining]
                    id2mark[def_id] = MARKED
                    useful_blocks.add(id2block[def_id])
                    worklist.append(def_id)

        curr_block = id2block[current_inst_id]
        for rdf_block in reverse_dominance_frontier[curr_block]:
            last_instr = None
            for block_instr in reversed(cfg[rdf_block][INSTRS]):
                last_instr = block_instr
                break
            if last_instr != None:
                last_instr_id = id(last_instr)
                id2mark[last_instr_id] = MARKED
                useful_blocks.add(id2block[last_instr_id])
                worklist.append(last_instr_id)

    # sweep phase
    final_instrs = []
    for instr in func[INSTRS]:
        instr_id = id(instr)
        if id2mark[instr_id] == MARKED:
            final_instrs.append(instr)
        else:
            if is_br(instr):
                pass
            elif is_label(instr):
                final_instrs.append(instr)
            elif is_jmp(instr):
                final_instrs.append(instr)
            else:
                # deleted
                pass
    return final_instrs


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
    """
    This is also incorrect, in that if a function has no side effects
    that does not mean it can be removed;
    in particular, one could have a function that is a simple infinite loop.
    These should be kept!
    """
    pass


def function_safe_adce(func):
    """
    From: http://www.cs.cmu.edu/afs/cs/academic/class/15745-s12/public/lectures/L14-SSA-Optimizations-1up.pdf
    Mark all instructions as Live that are:
        I/O
        Store into memory TODO: when Bril has memory instructions
        Terminator - RET
        Calls a function with side effects (e.g. most functions)
        Label

    Conservative Safer version of ADCE
    Keeps all Labels in Graph
    When an instruction in a block is live, add the terminator to that block automatically, e.g. jmp, ret, br
    When a backedge is detected heading in a block, add the terminator for the other block heading into this block
        - This keeps all loops in the program
        - Does not remove infinite loops that do nothing.
        - Use backedge detector for this 
    """
    # build important auxillary data structures (READ-ONLY)
    instrs = func[INSTRS]

    cfg = form_cfg_w_blocks(func)
    entry = list(cfg.keys())[0]
    cfg_w_exit = add_unique_exit_to_cfg(cfg, UNIQUE_CFG_EXIT)
    backedge_start_blocks = set(
        list(map(lambda pair: pair[1], get_backedges_w_cfg(cfg, entry))))
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
        curr_block = id2block[id(instr)]
        if is_io(instr) or is_ret(instr) or is_call(instr):
            # mark current instr as live
            marked_instrs[id(instr)] = LIVE
            # add arguments of current instr as live
            if ARGS in instr:
                for a in instr[ARGS]:
                    # add only if not an argument of the function
                    if a in def2id:
                        worklist.append(def2id[a])
            # add terminator for block for current instr
            for instr in reversed(cfg[curr_block][INSTRS]):
                if is_terminator(instr):
                    worklist.append(id(instr))
            # add the control dependency parent of this instruction's block
            for cd_block in control_dependence[curr_block]:
                for instr in reversed(cfg[cd_block][INSTRS]):
                    if is_terminator(instr):
                        worklist.append(id(instr))
        # add terminators for any start of a backedge
        if curr_block in backedge_start_blocks:
            for instr in reversed(cfg[curr_block][INSTRS]):
                if is_terminator(instr):
                    worklist.append(id(instr))

    # DO WORKLIST
    while worklist != []:
        instr_id = worklist.pop()
        if marked_instrs[instr_id] == LIVE:
            continue
        # Grab Operands of S
        marked_instrs[instr_id] = LIVE
        # add arguments of current_instr
        instr = id2instr[instr_id]
        if ARGS in instr:
            for a in instr[ARGS]:
                # add only if not an argument of the function
                if a in def2id:
                    worklist.append(def2id[a])
        # add terminator for block for current instr
        curr_block = id2block[instr_id]
        for inner_instr in reversed(cfg[curr_block][INSTRS]):
            if is_terminator(inner_instr):
                worklist.append(id(inner_instr))
        # add the control dependency parent of this instruction's block
        for cd_block in control_dependence[curr_block]:
            for inner_instr in reversed(cfg[cd_block][INSTRS]):
                if is_terminator(inner_instr):
                    worklist.append(id(inner_instr))
        # add terminators for any start of a backedge
        if curr_block in backedge_start_blocks:
            for inner_instr in reversed(cfg[curr_block][INSTRS]):
                if is_terminator(inner_instr):
                    worklist.append(id(inner_instr))

    # FINISH by keeping alive instructions
    final_instrs = []
    for instr_id in marked_instrs:
        if marked_instrs[instr_id] == LIVE:
            final_instrs.append(id2instr[instr_id])
        elif is_label(id2instr[instr_id]):
            final_instrs.append(id2instr[instr_id])
    return final_instrs


def function_adce(func):
    """
    From: http://www.cs.cmu.edu/afs/cs/academic/class/15745-s12/public/lectures/L14-SSA-Optimizations-1up.pdf
    Mark all instructions as Live that are:
        I/O
        Store into memory TODO: when Bril has memory instructions
        Terminator - RET
        Calls a function with side effects (e.g. most functions)
        Label

    NOTE: This algorithm is actually incorrect in that for infinite loops
    that do not have I/O or memory access or function call, the loop gets entirely
    eliminated. This is a consequence of the no-use conditions that are searched for.
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
        if is_io(instr) or is_jmp(instr) or is_ret(instr) or is_call(instr):
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
        elif is_label(id2instr[instr_id]):
            final_instrs.append(id2instr[instr_id])
    return final_instrs


def global_adce(program):
    """
    Aggressive Dead Code Elimination

    NOTE: The ADCE is actually incorrect in that for infinite loops
    that do not have I/O or memory access or function call, the loop gets entirely
    eliminated. This is a consequence of the no-use conditions that are searched for.

    NOTE: SAFE_ADCE should be conservatively sound
    """
    try:
        is_ssa(program)
    except:
        program = bril_to_ssa(program)
    for func in program[FUNCTIONS]:
        new_instrs = function_safe_adce(func)
        func[INSTRS] = new_instrs
    is_ssa(program)
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
