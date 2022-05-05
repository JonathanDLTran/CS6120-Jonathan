"""
Basic Loop Unrolling

TODO: How to identify loops that can be unrolled (e.g. a for loop)
IDEA: Can we feed the loop to a synthesizer sketch with the sketch already
being partly unrolled??

The sketch would have to be built around the Bril language though, or you 
would have to build your own sketcher.

The idea is given a natural loop N, you can sometimes unroll N in to a fixed degree
or completely.

Loop Header H 
Loop Bodies B 
---> 
H B B B B (N TIMES)... H B B B B (N TIMES)...

Where N is chosen appropriately large. A syntehsizer can figure out what N is
and prove that the new unrolled loop is equivalent to (H B) using an SMT equivalence
checker.


-------------

In basic unrolling, a natural loop is taken. We only consider loops that enter
and exit through the header of the natural loop, e.g. only single entry and exit
loops.

The branch MUST be in the header. The branch condition must be some affine combination
of integer based varaibles, e.g. ai + b 

The body of the loop must have an update on i in ONE place.

We also forbid side effects in the loop like print statements or function calls.

For this type of loop, we can immediately solve out how many iterations the loop should 
execute. We can then fully unroll the loop, and add the remainder at the end.

We can do a "cheaper" unroll for something like a while loop as well. Wikipedia
documents an unroll that keeps in branches. It would be nice to eliminate these branches
but sometimes there is no easy way. Perhaps that is where synthesis can be used.
"""

from copy import deepcopy
import json
import sys
import click

from bril_core_constants import ARGS, FUNCTIONS, LABEL, LABELS
from bril_core_utilities import build_br, build_jmp, build_label, build_void_ret, is_br, is_jmp, is_label

from cfg import form_cfg_w_blocks, SUCCS, PREDS, INSTRS, insert_into_cfg_w_blocks, join_cfg
from dominator_utilities import get_natural_loops


UNROLL_FACTOR = 8

HEADER_LABEL = "new.loop.header.label"
UNROLLING_EMERGENCY_RET_LABEL = "emergency.ret"

def gen_header_label(i: int):
    return f"{HEADER_LABEL}.{i}"


def loop_has_single_exit(natural_loop):
    assert type(natural_loop) == tuple
    assert len(natural_loop) == 4
    (_, _, _, exits) = natural_loop
    assert type(exits) == list
    return len(exits) == 1


def modify_header_branch(header_label, cfg, new_branch_label, br_arg_idx):
    """
    Changes the branch in a header to point elsewhere 
    """
    assert header_label in cfg
    assert br_arg_idx in [0, 1]
    header_instrs = cfg[header_label][INSTRS]
    num_branches = 0
    new_branch_instr = None
    for instr in header_instrs:
        if is_br(instr):
            num_branches += 1
            if br_arg_idx == 0:
                new_branch_instr = build_br(instr[ARGS][0], new_branch_label, instr[LABELS][1])
            else:
                new_branch_instr = build_br(instr[ARGS][0], instr[LABELS][0], new_branch_label)
    assert num_branches == 1 
    assert new_branch_instr != None
    new_header_instrs = []
    for instr in header_instrs:
        if is_br(instr):
            new_header_instrs.append(new_branch_instr)
        else:
            new_header_instrs.append(instr)
    cfg[header_label][INSTRS] = new_header_instrs
    return new_header_instrs


def modify_loop_jumps(loop_labels, cfg, old_header_label, new_header_label):
    for loop_label in loop_labels:
        assert loop_label in cfg
        block_instrs = cfg[loop_label][INSTRS]
        new_block_instrs = []
        num_changes = 0
        for instr in block_instrs:
            if is_jmp(instr) and instr[LABELS][0] == old_header_label:
                num_changes += 1
                new_jmp_instr = build_jmp(new_header_label)
                new_block_instrs.append(new_jmp_instr)
            else:
                new_block_instrs.append(instr)
        assert 0 <= num_changes <= 1
        cfg[loop_label][INSTRS] = new_block_instrs


def renumber_loop_body_labels(loop_instrs, i, excluded_labels):
    new_loop_instrs = []
    for instr in loop_instrs:
        if is_jmp(instr):
            if instr[LABELS][0] not in excluded_labels:
                new_jmp = build_jmp(f"{instr[LABELS][0]}.{i}")
                new_loop_instrs.append(new_jmp)
            else:
                new_loop_instrs.append(instr)
        elif is_br(instr):
            new_br = build_br(instr[ARGS][0], instr[LABELS][0], instr[LABELS][1]) 
            new_loop_instrs.append(new_br)
        elif is_label(instr):
            new_label = build_label(f"{instr[LABEL]}.{i}")
            new_loop_instrs.append(new_label)
        else:
            new_loop_instrs.append(instr)
    return new_loop_instrs


def get_br_index(header_instrs, header_name, exits):
    for instr in header_instrs:
        if is_br(instr):
            labels = instr[LABELS]
            assert len(labels) == 2
            for i, l in enumerate(labels):
                for (inside_loop, outside_loop) in exits:
                    if inside_loop == header_name and outside_loop == l:
                        assert 0 <= i <= 1
                        return (i, labels[1] if i == 0 else labels[0])
    raise RuntimeError(f"No Branch Found in Loop Header: {header_instrs}. ")


def unroll_func(func):
    # TODO: header cannot have side effects like calls or such
    cfg = form_cfg_w_blocks(func)
    natural_loops = get_natural_loops(func)

    # add emergency exit to the program, and append stuff to the cfg afterwaerdss
    insert_into_cfg_w_blocks(UNROLLING_EMERGENCY_RET_LABEL, [build_void_ret()], [], [], cfg)

    # start unrolling
    for loop in natural_loops:
        if not loop_has_single_exit(loop):
            continue

        (natural_loop, _, header, exits) = loop

        header_labels = []
        for i in range(UNROLL_FACTOR):
            for block in natural_loop:
                new_header_name = gen_header_label(i)
                header_labels.append(new_header_name)
                if block == header:
                    header_instrs = cfg[header][INSTRS]
                    if is_label(header_instrs[0]):
                        header_instrs = header_instrs[1:]
                    new_header_label = build_label(new_header_name)
                    insert_into_cfg_w_blocks(new_header_name, [new_header_label] + header_instrs, [], [], cfg)
                else:
                    block_instrs = cfg[block][INSTRS]
                    new_block_instrs = renumber_loop_body_labels(deepcopy(block_instrs), i, [header])
                    insert_into_cfg_w_blocks(f"{new_header_name}.{i}", new_block_instrs, [], [], cfg)
                

        # Change preds and succs, modify the blocks as necessary
        # start with original header
        assert len(header_labels) != 0
        br_arg_index, loop_entry_label = get_br_index(cfg[header][INSTRS], header, exits)
        modify_header_branch(header, cfg, header_labels[0], br_arg_index)
        original_header_succs = cfg[header][SUCCS] 
        assert len(original_header_succs) == 2
        original_header_succs = list(set(original_header_succs).difference({header}))[0]
        cfg[header][SUCCS] = [header_labels[0]]

        # enter unrolled loop headers and bodies, preds and succs
        loop_labels = []
        for block in natural_loop:
            if block != header:
                loop_labels.append(block)

        prev_header = header
        for i in range(UNROLL_FACTOR - 1):
            current_header = header_labels[i]
            next_header = header_labels[i + 1]
            modify_header_branch(current_header, cfg, next_header, br_arg_index)
            modify_header_branch(current_header, cfg, f"{loop_entry_label}.{i}", 1 if br_arg_index == 0 else 0)
            modify_loop_jumps(loop_labels, cfg, header, current_header)
            # preds
            cfg[current_header][PREDS] = [prev_header]
            prev_header = current_header
            # succs
            cfg[current_header][SUCCS] = [next_header]

        # handle final unrolled loop header and body
        final_header = header_labels[i]
        modify_header_branch(final_header, cfg, original_header_succs, br_arg_index)
        modify_loop_jumps(loop_labels, cfg, header, final_header)
        # preds
        cfg[current_header][PREDS] = [prev_header]
        # succs
        cfg[current_header][SUCCS] = [original_header_succs]

        # fix up out of original loop preds
        cfg[original_header_succs][SUCCS] = [final_header]


    # DO JOINING ON CFG
    new_instrs = join_cfg(cfg)
    func[INSTRS] = new_instrs
    return func

def basic_unroll_prog(prog):
    for func in prog[FUNCTIONS]:
        unroll_func(func)
    return prog



@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = basic_unroll_prog(prog)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
