from copy import deepcopy
from collections import OrderedDict
import click
import sys
import json

from cfg import form_cfg_w_blocks, insert_into_cfg, join_cfg, INSTRS, SUCCS, PREDS
from reaching_definitions import reaching_defs_func
from dominator_utilities import get_natural_loops, build_dominance_tree
from bril_core_constants import *


LOOP_INVARIANT = True
NOT_LOOP_INVARIANT = not LOOP_INVARIANT


LOOP_PREHEADER_COUNTER = 0
NEW_LOOP_PREHEADER = "new.loop.preheader"


def gen_loop_preheader():
    global LOOP_PREHEADER_COUNTER
    LOOP_PREHEADER_COUNTER += 1
    return f"{NEW_LOOP_PREHEADER}.{LOOP_PREHEADER_COUNTER}"


def insert_preheaders(natural_loops, cfg):
    headers = set()
    preheadermap = OrderedDict()
    backedgemap = OrderedDict()
    for _, (A, _), header in natural_loops:
        if header not in backedgemap:
            backedgemap[header] = [A]
        else:
            backedgemap[header].append(A)
    for _, _, header in natural_loops:
        if header in headers:
            # loop header shared with another prior loop header
            continue
        preheader = gen_loop_preheader()
        headers.add(header)
        preheadermap[header] = preheader
        insert_into_cfg(preheader, backedgemap[header], header, cfg)
    return preheadermap


def identify_li_recursive(cfg, dominance_tree, reaching_definitions, loop_instrs, loop_blocks, basic_block, instrs_invariant_map, var_invariant_map):
    (in_dict, _) = reaching_definitions
    instrs = cfg[basic_block][INSTRS]
    for instr in instrs:
        # constants
        if VALUE in instr and DEST in instr:
            instrs_invariant_map[id(instr)] = LOOP_INVARIANT
            var_invariant_map[instr[DEST]] = LOOP_INVARIANT
        # consider instructions with arguments
        elif ARGS in instr and DEST in instr:
            args = instr[ARGS]
            dst = instr[DEST]
            is_loop_invariant = True
            for x in args:
                # condition 1: Arguments are defined by
                # values defined outside of loop
                x_reaches_from_outside_loop = True
                for block in cfg:
                    for (_, var) in in_dict[block]:
                        if var == dst and block in loop_blocks:
                            x_reaches_from_outside_loop = False
                            break
                    if not x_reaches_from_outside_loop:
                        break
                if x_reaches_from_outside_loop:
                    continue

                # condition 2: Arguments are defined exactly once
                # inside the loop, and the argument itself was
                # marked as loop invariant
                x_def_counter = 0
                for loop_instr in loop_instrs:
                    if DEST in loop_instr:
                        other_dst = loop_instr[DEST]
                        if other_dst == dst:
                            x_def_counter += 1
                if x_def_counter == 1 and var_invariant_map[x]:
                    continue

                is_loop_invariant = False
                break

            if is_loop_invariant:
                instrs_invariant_map[id(instr)] = LOOP_INVARIANT
                var_invariant_map[dst] = LOOP_INVARIANT
            else:
                instrs_invariant_map[id(instr)] = NOT_LOOP_INVARIANT
                var_invariant_map[dst] = NOT_LOOP_INVARIANT
        else:
            instrs_invariant_map[id(instr)] = NOT_LOOP_INVARIANT

    children = dominance_tree[basic_block]
    for c in children:
        if c in loop_blocks:
            instrs_invariant_map = identify_li_recursive(
                cfg, dominance_tree, reaching_definitions, loop_instrs, loop_blocks, c, instrs_invariant_map, deepcopy(var_invariant_map))

    return instrs_invariant_map


def identify_loop_invariant_instrs(cfg, loop_blocks, loop_instrs, loop_header, reaching_definitions, dominance_tree):
    """
    For a Given Loop, identify those instructions in the loop that are loop invariant
    """
    assert loop_header in loop_blocks

    # mark all insdtructions as not loop invariant
    instrs_invariant_map = OrderedDict()
    for loop_instr in loop_instrs:
        instrs_invariant_map[id(loop_instr)] = NOT_LOOP_INVARIANT

    continue_while = True
    while continue_while:
        old_loop_instrs = deepcopy(loop_instrs)

        var_invariant_map = OrderedDict()
        for loop_instr in loop_instrs:
            if DEST in loop_instr:
                var_invariant_map[loop_instr[DEST]] = NOT_LOOP_INVARIANT
        instrs_invariant_map = identify_li_recursive(cfg, dominance_tree, reaching_definitions, loop_instrs, loop_blocks, loop_header,
                                                     instrs_invariant_map, var_invariant_map)

        if loop_instrs == old_loop_instrs:
            continue_while = False

    return instrs_invariant_map


def move_loop_invariant_instrs():
    pass


def loop_licm(natural_loop, cfg, preheadermap, reaching_definitions, dominance_tree):
    # Grab the instructions in a loop
    (loop_blocks, _, header) = natural_loop
    loop_instrs = []
    for block_name in cfg:
        if block_name in loop_blocks:
            loop_instrs += cfg[block_name][INSTRS]

    loop_instrs_map = identify_loop_invariant_instrs(
        cfg, loop_blocks, loop_instrs, header, reaching_definitions, dominance_tree)

    for instr in loop_instrs:
        if id(instr) in loop_instrs_map:
            print(f"{id(instr)} | {instr} | {loop_instrs_map[id(instr)]}")


def func_licm(func):
    natural_loops = get_natural_loops(func)
    cfg = form_cfg_w_blocks(func)
    preheadermap = insert_preheaders(natural_loops, cfg)
    reaching_definitions = reaching_defs_func(func)
    dominance_tree, _ = build_dominance_tree(func)

    for natural_loop in natural_loops:
        loop_licm(natural_loop, cfg, preheadermap,
                  reaching_definitions, dominance_tree)

    return join_cfg(cfg)


def licm_main(program):
    """
    LICM wrapper function
    """
    for func in program["functions"]:
        modified_func_instrs = func_licm(func)
        func["instrs"] = modified_func_instrs
    return program


@click.command()
@click.option('--licm', default=False, help='Run Loop Invariant Code Motion.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(licm, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if licm:
        final_prog = licm_main(prog)
    else:
        final_prog = prog
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
