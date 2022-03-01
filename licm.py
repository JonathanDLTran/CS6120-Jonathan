from copy import deepcopy
from collections import OrderedDict
import click
import sys
import json

from cfg import form_cfg_w_blocks, insert_into_cfg, join_cfg, INSTRS
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
    for _, (A, _), header, _ in natural_loops:
        if header not in backedgemap:
            backedgemap[header] = [A]
        else:
            backedgemap[header].append(A)
    for _, _, header, _ in natural_loops:
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
                for loop_instr, _ in loop_instrs:
                    if DEST in loop_instr:
                        other_dst = loop_instr[DEST]
                        if other_dst == dst:
                            x_def_counter += 1
                if x_def_counter == 1 and (x not in var_invariant_map or var_invariant_map[x]):
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
    for loop_instr, _ in loop_instrs:
        instrs_invariant_map[id(loop_instr)] = NOT_LOOP_INVARIANT

    continue_while = True
    while continue_while:
        old_loop_instrs = deepcopy(loop_instrs)

        var_invariant_map = OrderedDict()
        for loop_instr, _ in loop_instrs:
            if DEST in loop_instr:
                var_invariant_map[loop_instr[DEST]] = NOT_LOOP_INVARIANT
        instrs_invariant_map = identify_li_recursive(cfg, dominance_tree, reaching_definitions, loop_instrs, loop_blocks, loop_header,
                                                     instrs_invariant_map, var_invariant_map)

        if loop_instrs == old_loop_instrs:
            continue_while = False

    return instrs_invariant_map


def gather_nodes(node, dominator_tree, natural_loop_nodes):
    nodes = [node]
    for c in dominator_tree[node]:
        if c in natural_loop_nodes:
            nodes += gather_nodes(c, dominator_tree, natural_loop_nodes)
    return nodes


def filter_loop_invariant_instrs(cfg, natural_loop, dominator_tree, loop_instrs, loop_instrs_map, id2instr):
    """
    Filter loop invariant insdtructions to only those that can be moved out of the loop
    """
    (natural_loop_nodes, _, header, exits) = natural_loop

    # loop invariant status fklter
    status_filter = []
    for identifier, status in loop_instrs_map.items():
        if status:
            status_filter.append(identifier)

    # check instruction dominates all uses in the loop
    dominate_filter = []
    for identifier in status_filter:
        def_instr, identifier_block = id2instr[identifier]
        dst = def_instr[DEST]

        # get position in block
        position = None
        for i, instr in enumerate(cfg[identifier_block][INSTRS]):
            if id(instr) == identifier:
                position = i
                break
        assert position != None

        # interblock check
        does_dominate = True
        for i, instr in enumerate(cfg[identifier_block][INSTRS]):
            if ARGS in instr and dst in instr[ARGS]:
                if i < position:
                    does_dominate = False
                    break

        # accumulate all uses
        dominated_blocks = set(gather_nodes(
            identifier_block, dominator_tree, natural_loop_nodes))
        all_loop_dominated_blocks = set(gather_nodes(
            header, dominator_tree, natural_loop_nodes
        ))
        does_not_dominate_blocks = all_loop_dominated_blocks.difference(
            dominated_blocks)

        for block in does_not_dominate_blocks:
            block_instrs = cfg[block][INSTRS]
            for instr in block_instrs:
                if ARGS in instr and dst in instr[ARGS]:
                    does_dominate = False
                    break

        if does_dominate:
            dominate_filter.append(identifier)

    # check no other definitions in same loop,
    def_filter = []
    for identifier in dominate_filter:
        def_instr, _ = id2instr[identifier]
        dest = def_instr[DEST]
        dest_count = 0
        for instr, _ in loop_instrs:
            if DEST in instr and instr[DEST] == dest:
                dest_count += 1

        if dest_count <= 1:
            def_filter.append(identifier)

    # check instruction dominates all exits
    exit_filter = []
    for identifier in def_filter:
        _, identifier_block = id2instr[identifier]
        dominated_blocks = set(gather_nodes(
            identifier_block, dominator_tree, natural_loop_nodes))

        dominates_exits = True
        for (start_node, _) in exits:
            if start_node not in dominated_blocks:
                dominates_exits = False

        if dominates_exits:
            exit_filter.append(identifier)

    return exit_filter


def insert_into_bb(cfg, basic_block, instr):
    instrs = cfg[basic_block][INSTRS]
    if len(instrs) > 0 and OP in instrs[-1] and instrs[-1][OP] in TERMINATORS:
        instrs.insert(-1, instr)
        cfg[basic_block][INSTRS] = instrs
    else:
        cfg[basic_block][INSTRS].append(instr)


def remove_from_bb(cfg, basic_block, identifier):
    new_instrs = []
    for instr in cfg[basic_block][INSTRS]:
        if id(instr) != identifier:
            new_instrs.append(instr)
    cfg[basic_block][INSTRS] = new_instrs


def move_instructions(cfg, header, preheadermap, identifiers_to_move, id2instr):
    for identifier in identifiers_to_move:
        instr, basic_block = id2instr[identifier]
        preheader = preheadermap[header]
        insert_into_bb(cfg, preheader, instr)
        remove_from_bb(cfg, basic_block, identifier)


def loop_licm(natural_loop, cfg, preheadermap, reaching_definitions, dominance_tree):
    # Grab the instructions in a loop
    (loop_blocks, _, header, _) = natural_loop
    loop_instrs = []
    for block_name in cfg:
        if block_name in loop_blocks:
            for instr in cfg[block_name][INSTRS]:
                loop_instrs.append((instr, block_name))

    loop_instrs_map = identify_loop_invariant_instrs(
        cfg, loop_blocks, loop_instrs, header, reaching_definitions, dominance_tree)

    # for instr, block_name in loop_instrs:
    #     if id(instr) in loop_instrs_map:
    #         print(
    #             f"{id(instr)} | {block_name} | {instr} | {loop_instrs_map[id(instr)]}")

    # buold map from id to identifier
    id2instr = OrderedDict()
    for identifier in loop_instrs_map:
        for instr, block_name in loop_instrs:
            if id(instr) == identifier:
                id2instr[identifier] = (instr, block_name)

    identifiers_to_move = filter_loop_invariant_instrs(
        cfg, natural_loop, dominance_tree, loop_instrs, loop_instrs_map, id2instr)

    move_instructions(cfg, header, preheadermap, identifiers_to_move, id2instr)

    return cfg


def func_licm(func):
    natural_loops = get_natural_loops(func)
    cfg = form_cfg_w_blocks(func)
    preheadermap = insert_preheaders(natural_loops, cfg)
    reaching_definitions = reaching_defs_func(func)
    dominance_tree, _ = build_dominance_tree(func)

    for natural_loop in natural_loops:
        cfg = loop_licm(natural_loop, cfg, preheadermap,
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
