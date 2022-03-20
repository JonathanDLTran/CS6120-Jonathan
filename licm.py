from copy import deepcopy
from collections import OrderedDict
import click
import sys
import json

from cfg import form_cfg_w_blocks, join_cfg, INSTRS
from reaching_definitions import reaching_defs_func
from dominator_utilities import get_natural_loops, build_dominance_tree
from bril_core_utilities import has_side_effects, is_label, is_jmp, is_br
from bril_core_constants import *


LOOP_INVARIANT = True
NOT_LOOP_INVARIANT = not LOOP_INVARIANT


LOOP_PREHEADER_COUNTER = 0
NEW_LOOP_PREHEADER = "new.loop.preheader"


NEW_CFG_LABEL = "new.cfg.label"
NEW_CFG_LABEL_IDX = 0


def gen_loop_preheader():
    global LOOP_PREHEADER_COUNTER
    LOOP_PREHEADER_COUNTER += 1
    return f"{NEW_LOOP_PREHEADER}.{LOOP_PREHEADER_COUNTER}"


def insert_preheaders(natural_loops, instrs_w_blocks):
    headers = set()
    preheadermap = OrderedDict()
    backedgemap = OrderedDict()
    preheaders = set()
    for _, (A, _), header, _ in natural_loops:
        if header not in backedgemap:
            backedgemap[header] = [A]
        else:
            backedgemap[header].append(A)
    new_instrs = []
    for (instr, instr_block) in instrs_w_blocks:
        if is_label(instr):
            for natural_loop_blocks, _, header, _ in natural_loops:
                if header == instr[LABEL]:
                    if header in headers:
                        # loop header shared with another prior loop header
                        continue
                    headers.add(header)
                    preheader = gen_loop_preheader()
                    preheaders.add(preheader)
                    preheadermap[header] = preheader
                    new_preheader_instr = {LABEL: preheader}

                    for (inner_instr, block) in instrs_w_blocks:
                        if (is_br(inner_instr) or is_jmp(inner_instr)) and block not in natural_loop_blocks:
                            if header in inner_instr[LABELS]:
                                new_labels = []
                                for label in inner_instr[LABELS]:
                                    if label != header:
                                        new_labels.append(label)
                                    else:
                                        new_labels.append(preheader)
                                inner_instr[LABELS] = new_labels
                    for (inner_instr, block) in new_instrs:
                        if is_br(inner_instr) or is_jmp(inner_instr) and block not in preheaders and block not in natural_loop_blocks:
                            if header in inner_instr[LABELS]:
                                new_labels = []
                                for label in inner_instr[LABELS]:
                                    if label != header:
                                        new_labels.append(label)
                                    else:
                                        new_labels.append(preheader)
                                inner_instr[LABELS] = new_labels

                    new_instrs.append((new_preheader_instr, preheader))
        new_instrs.append((instr, instr_block))

    final_instrs = list(map(lambda pair: pair[0], new_instrs))
    return preheadermap, final_instrs


def identify_li_recursive(cfg, reaching_definitions, func_args, loop_blocks, basic_block, instrs_invariant_map, var_invariant_map):
    (in_dict, _) = reaching_definitions
    for basic_block in loop_blocks:
        instrs = cfg[basic_block][INSTRS]
        for instr in instrs:
            # constants
            if VALUE in instr and DEST in instr:
                # constants have no arguments, so we just need to make sure there is exactly 1 definition in the loop
                val_is_loop_invariant = True
                for other_block in loop_blocks:
                    for other_instr in cfg[other_block][INSTRS]:
                        if DEST in other_instr and id(instr) != id(other_instr):
                            if other_instr[DEST] == instr[DEST]:
                                val_is_loop_invariant = False
                instrs_invariant_map[id(
                    instr)] = LOOP_INVARIANT if val_is_loop_invariant else NOT_LOOP_INVARIANT
                var_invariant_map[instr[DEST]
                                  ] = LOOP_INVARIANT if val_is_loop_invariant else NOT_LOOP_INVARIANT
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
                    # inside the entire function (not just loop), and the argument itself was
                    # marked as loop invariant
                    # We make sure to add function arguments as definitions
                    x_def_counter = 0
                    for a in func_args:
                        if a == dst:
                            x_def_counter += 1
                    for def_instr in instrs:
                        if DEST in def_instr:
                            other_dst = def_instr[DEST]
                            if other_dst == dst:
                                x_def_counter += 1
                    if x_def_counter == 1 and (x in var_invariant_map and var_invariant_map[x]):
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

    return instrs_invariant_map, var_invariant_map


def identify_loop_invariant_instrs(cfg, func_args, loop_blocks, loop_instrs, loop_header, reaching_definitions):
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
        instrs_invariant_map, var_invariant_map = identify_li_recursive(cfg, reaching_definitions, func_args, loop_blocks, loop_header,
                                                                        instrs_invariant_map, var_invariant_map)

        if loop_instrs == old_loop_instrs:
            continue_while = False

    return instrs_invariant_map, var_invariant_map


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
        def_instr, identifier_block = id2instr[identifier]
        dominated_blocks = set(gather_nodes(
            identifier_block, dominator_tree, natural_loop_nodes))

        dominates_exits = True
        for (start_node, _) in exits:
            if start_node not in dominated_blocks:
                dominates_exits = False

        # Side condition: If variable is dead after loop and has no side effects
        used_after_loop = False
        for after_block in cfg:
            if after_block not in natural_loop_nodes:
                for after_instr in cfg[after_block][INSTRS]:
                    if ARGS in after_instr and DEST in def_instr:
                        for arg in after_instr[ARGS]:
                            if arg == def_instr[DEST]:
                                used_after_loop = True

        no_side_effects = False
        if not has_side_effects(def_instr):
            no_side_effects = True

        if not used_after_loop and no_side_effects:
            dominates_exits = True

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


def recursively_move_instructions(cfg, header, preheadermap, identifiers_to_move, destination, id2instr, vars_inside_loop, moved_vars):
    """
    Move instructions in an order such that argument dependencies are correct
    If a = b op c depends on b and c, and b is inisde the loop, then b must be computed first
    If c is otuside the looop, it does not need to be computed.

    If b cannot be moved, e.g. was a div instruction, then neither can a.
    """
    identifier = None
    for curr_identifier in identifiers_to_move:
        instr, _ = id2instr[curr_identifier]
        dst = instr[DEST]
        if dst == destination:
            identifier = curr_identifier
    if identifier == None:
        return False

    instr, basic_block = id2instr[identifier]
    dst = instr[DEST]

    if ARGS in instr:
        for a in instr[ARGS]:
            if a not in moved_vars and a in vars_inside_loop:
                result = recursively_move_instructions(
                    cfg, header, preheadermap, identifiers_to_move, a, id2instr, vars_inside_loop, moved_vars)
                if not result:
                    return False

    preheader = preheadermap[header]
    insert_into_bb(cfg, preheader, instr)
    remove_from_bb(cfg, basic_block, identifier)

    moved_vars.add(dst)
    return True


def move_instructions(cfg, header, preheadermap, identifiers_to_move, id2instr, vars_inside_loop, moved_vars):
    for identifier in identifiers_to_move:
        instr, basic_block = id2instr[identifier]

        skip_identifier = False
        if ARGS in instr:
            for a in instr[ARGS]:
                if a not in moved_vars and a in vars_inside_loop:
                    result = recursively_move_instructions(
                        cfg, header, preheadermap, identifiers_to_move, a, id2instr, vars_inside_loop, moved_vars)
                    if not result:
                        skip_identifier = True
        if skip_identifier:
            continue

        dst = instr[DEST]
        if dst in moved_vars:
            continue

        preheader = preheadermap[header]
        insert_into_bb(cfg, preheader, instr)
        remove_from_bb(cfg, basic_block, identifier)

        moved_vars.add(dst)
    return


def loop_licm(natural_loop, cfg, func_args, preheadermap, reaching_definitions, dominance_tree):
    # Grab the instructions in a loop
    (loop_blocks, _, header, _) = natural_loop
    loop_instrs = []
    vars_inside_loop = set()
    for block_name in cfg:
        if block_name in loop_blocks:
            for instr in cfg[block_name][INSTRS]:
                loop_instrs.append((instr, block_name))
                if DEST in instr:
                    vars_inside_loop.add(instr[DEST])

    loop_instrs_map, _ = identify_loop_invariant_instrs(
        cfg, func_args, loop_blocks, loop_instrs, header, reaching_definitions)

    # buold map from id to identifier
    id2instr = OrderedDict()
    for identifier in loop_instrs_map:
        for instr, block_name in loop_instrs:
            if id(instr) == identifier:
                id2instr[identifier] = (instr, block_name)

    identifiers_to_move = filter_loop_invariant_instrs(
        cfg, natural_loop, dominance_tree, loop_instrs, loop_instrs_map, id2instr)

    move_instructions(cfg, header, preheadermap, identifiers_to_move,
                      id2instr, vars_inside_loop, set())

    return cfg


def func_licm(func):
    natural_loops = get_natural_loops(func)
    old_cfg = form_cfg_w_blocks(func)
    instrs_w_blocks = []
    for block in old_cfg:
        for instr in old_cfg[block][INSTRS]:
            instrs_w_blocks.append((instr, block))
    preheadermap, new_instrs = insert_preheaders(
        natural_loops, instrs_w_blocks)
    func[INSTRS] = new_instrs
    cfg = form_cfg_w_blocks(func)
    reaching_definitions = reaching_defs_func(func)
    dominance_tree, _ = build_dominance_tree(func)
    func_args = []
    if ARGS in func:
        for a in func[ARGS]:
            func_args.append(a[NAME])

    for natural_loop in natural_loops:
        cfg = loop_licm(natural_loop, cfg, func_args, preheadermap,
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
