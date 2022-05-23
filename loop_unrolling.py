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

from bril_core_constants import ARGS, COMP_OPS, EQ, FUNCTIONS, GE, GT, LABEL, LABELS, LE, LT, OP, VALUE
from bril_core_utilities import build_br, build_jmp, build_label, build_void_ret, get_args, get_br_labels, has_args, has_dest, get_dest, is_add, is_br, is_cmp, is_const, is_jmp, is_label, is_sub

from cfg import form_cfg_w_blocks, SUCCS, PREDS, INSTRS, insert_into_cfg_w_blocks, join_cfg
from dominator_utilities import get_dominators, get_natural_loops, get_strict_dominators

UNROLL_FACTOR = 2
assert UNROLL_FACTOR >= 2

HEADER_LABEL = "new.loop.header.label"
UNROLLING_EMERGENCY_RET_LABEL = "emergency.ret"


def gen_header_label(i: int):
    return f"{HEADER_LABEL}.{i}"


########################### FULLY UNROLL #######################################


class FullyUnrollableLoop(object):
    """
    Represents a Fully Unrollable Loop
    """

    def __init__(self, header, body, var_name, start_val, bump_val, end_val, is_incr, comp_op):
        assert type(header) == str
        assert type(body) == set  # of str
        assert type(var_name) == str
        assert type(start_val) == int
        assert type(bump_val) == int
        assert bump_val == 1  # for now, has to be 1
        assert type(end_val) == int
        assert type(is_incr) == bool
        assert comp_op in COMP_OPS

        self.header = header
        self.body = body
        self.var_name = var_name
        self.start_val = start_val
        self.bump_val = bump_val
        self.end_val = end_val
        self.is_incr = is_incr
        self.comp_op = comp_op

    def get_niters(self):
        """
        Assumes Loop Guaranteed to Terminate
        """
        if self.end_val == self.start_val:
            if self.comp_op in (EQ, LE, GE):
                return 0
            else:
                raise RuntimeError(f"Please check will terminate before")
        elif self.end_val > self.start_val:
            if self.comp_op == EQ:
                return self.end_val - self.start_val + 1
            elif self.comp_op == LE:
                return self.end_val - self.start_val + 1
            elif self.comp_op == GE:
                return 0
            elif self.comp_op == LT:
                return self.end_val - self.start_val
            elif self.comp_op == GT:
                return 0
            else:
                RuntimeError(f"Unmatched comparison operation {self.comp_op}.")
        else:
            if self.comp_op == EQ:
                return self.start_val - self.end_val + 1
            elif self.comp_op == LE:
                return 0
            elif self.comp_op == GE:
                return self.start_val - self.end_val + 1
            elif self.comp_op == LT:
                return 0
            elif self.comp_op == GT:
                return self.start_val - self.end_val
            else:
                RuntimeError(f"Unmatched comparison operation {self.comp_op}.")

    def will_terminate(self):
        """
        Conservatively decide if loop will terminate
        """
        if self.end_val == self.start_val:
            if self.comp_op == LT and self.is_incr:
                return False
            elif self.comp_op == GT and not self.is_incr:
                return False
            return True
        elif self.end_val > self.start_val:
            if not self.is_incr:
                return False
            return True
        else:
            if self.is_incr:
                return False
            return True

    def cmp_to_str(self):
        if self.comp_op == EQ:
            return "=="
        elif self.comp_op == GT:
            return ">"
        elif self.comp_op == LT:
            return "<"
        elif self.comp_op == GE:
            return ">="
        elif self.comp_op == LE:
            return "<="
        raise RuntimeError(f"Unmatched comparison operation {self.comp_op}.")

    def is_incr_to_str(self):
        if self.is_incr:
            return "+"
        return "-"

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        return f"{self.var_name} := {self.start_val}; {self.var_name} {self.cmp_to_str()} {self.end_val}; {self.var_name} {self.is_incr_to_str()}= {self.bump_val}"


def is_fully_unrollable(natural_loop, natural_loops, cfg, domby):
    """
    A loop is fully unrollable if the loop has:
    - Exactly 1 exit, via the header
    - Loop is not nested (unfortunately, not handled now, even though that would be a LOT more performant)
    - Exactly 1 loop variable, an indexed variable in integers
        - Which has a maximum number of iterations (set outside the loop)
        - A start value
        - Exactly one increment in the loop
        - Exactly 1 jump back to the header
        - Loop Iteration conditions guarantee loop will terminate
    """
    if not loop_has_single_exit(natural_loop):
        return False
    if loop_is_nested(natural_loop, natural_loops):
        return False
    if not loop_has_single_jmp_to_header(natural_loop, cfg):
        return False
    if not loop_has_single_br_in_header(natural_loop, cfg):
        return False
    if not loop_has_no_br_to_header(natural_loop, cfg):
        return False
    has_one_iter_var = loop_has_one_iteration_var(natural_loop, cfg, domby)
    if type(has_one_iter_var) == bool and has_one_iter_var == False:
        return False
    if not has_one_iter_var.will_terminate():
        return False
    return has_one_iter_var


def fully_unroll_loop(unrollable_object, natural_loop, cfg):
    """
    Fully Unrolls Natural Loop in CFG

    DOES NOT ATTEMPT TO CHANGE SUCCS AND PREDS
    """
    (natural_loop, _, header, exits) = natural_loop

    assert unrollable_object.will_terminate()
    unroll_niter = unrollable_object.get_niters()

    # if the loop never executes, or executes once, just bail
    if 0 <= unroll_niter <= 1:
        return

    # Begin Unrolling Process

    assert unroll_niter >= 2

    # grab non-header loop labels
    loop_labels = []
    for block in natural_loop:
        if block != header:
            loop_labels.append(block)

    # grab loop exit label
    assert len(exits) == 1
    loop_exit_name = None
    for (a, b) in exits:
        if a not in natural_loop:
            loop_exit_name = a
        elif b not in natural_loop:
            loop_exit_name = b
        break
    assert loop_exit_name != None

    # grab loop entry name
    loop_entry_name = None
    for header_instr in cfg[header][INSTRS]:
        if is_br(header_instr):
            labels = get_br_labels(header_instr)
            for label in labels:
                if label in loop_labels:
                    loop_entry_name = label
    assert loop_entry_name != None

    # insert  __unroll_niter - 1__ copies of solely loop bodies into the cfg [exclude loop headers]
    for i in range(unroll_niter - 1):
        # TODO: Header must be added as it might change state; but remove branch from header

        # now add in the loop body blocks themselves
        for block in natural_loop:
            if block != header:
                block_instrs = cfg[block][INSTRS]
                # relabel labels to be unique in each iteration of unrolled loop
                new_block_instrs = renumber_loop_body_labels(
                    deepcopy(block_instrs), i, [header])
                insert_into_cfg_w_blocks(
                    f"{block}.{i}", new_block_instrs, [], [], cfg)
            else:
                block_instrs = cfg[block][INSTRS]
                new_block_instrs = renumber_loop_body_labels(
                    deepcopy(block_instrs), i, [header])
                # replace the branch with a jump to the appropriate loop body
                final_block_instrs = []
                for header_instr in new_block_instrs:
                    if is_br(header_instr):
                        new_jmp_instr = build_jmp(f"{loop_entry_name}.{i}")
                        final_block_instrs.append(new_jmp_instr)
                    else:
                        final_block_instrs.append(header_instr)
                insert_into_cfg_w_blocks(
                    f"{header}.{i}", final_block_instrs, [], [], cfg)

        # change any jump labels to header to next header label
        ith_iter_labels = []
        for label in loop_labels:
            ith_iter_labels.append(f"{label}.{i}")
        modify_loop_jumps(ith_iter_labels, cfg, header, f"{header}.{i + 1}")

    # modify original [aka FIRST] loop iteration to jump to first unroll header rather than header
    first_unroll_header = f"{header}.{0}"
    modify_loop_jumps(loop_labels, cfg, header, first_unroll_header)

    # add final extra header at end, because headers are always checked once more
    header_instrs = cfg[header][INSTRS]
    new_header_instrs = renumber_loop_body_labels(
        deepcopy(header_instrs), i + 1, [header])
    # replace the branch with a jump to the appropriate loop body
    final_header_instrs = []
    for header_instr in new_header_instrs:
        if is_br(header_instr):
            new_jmp_instr = build_jmp(loop_exit_name)
            final_header_instrs.append(new_jmp_instr)
        else:
            final_header_instrs.append(header_instr)
    insert_into_cfg_w_blocks(
        f"{header}.{i + 1}", final_header_instrs, [], [], cfg)


def fully_unroll_func(func):
    cfg = form_cfg_w_blocks(func)
    _, domby = get_dominators(func)
    natural_loops = get_natural_loops(func)

    # add emergency exit to the program, and append stuff to the cfg afterwaerdss
    insert_into_cfg_w_blocks(UNROLLING_EMERGENCY_RET_LABEL, [
                             build_void_ret()], [], [], cfg)

    # start unrolling
    for natural_loop in natural_loops:
        is_unrollable = is_fully_unrollable(
            natural_loop, natural_loops, cfg, domby)
        if type(is_unrollable) == bool and is_unrollable == False:
            continue
        fully_unroll_loop(is_unrollable, natural_loop, cfg)

    # DO JOINING ON CFG
    new_instrs = join_cfg(cfg)
    func[INSTRS] = new_instrs
    return func


def fully_unroll_prog(prog):
    for func in prog[FUNCTIONS]:
        fully_unroll_func(func)
    return prog


########################### BASIC UNROLL #######################################


def loop_is_nested(natural_loop, natural_loops):
    (blocks, _, _, _) = natural_loop
    for nl in natural_loops:
        if nl != natural_loop:
            (other_blocks, _, _, _) = nl
            if set(blocks).issubset(set(other_blocks)):
                return True
    return False


def loop_has_single_jmp_to_header(natural_loop, cfg):
    (loop_blocks, _, header, _) = natural_loop
    non_header_blocks = set(loop_blocks).difference({header})
    jmps_to_header = 0
    for block in non_header_blocks:
        for instr in cfg[block][INSTRS]:
            if is_jmp(instr) and instr[LABELS][0] == header:
                jmps_to_header += 1
    return jmps_to_header == 1


def loop_has_no_br_to_header(natural_loop, cfg):
    (loop_blocks, _, header, _) = natural_loop
    non_header_blocks = set(loop_blocks).difference({header})
    brs_to_header = 0
    for block in non_header_blocks:
        for instr in cfg[block][INSTRS]:
            if is_br(instr) and header in get_br_labels(instr):
                brs_to_header += 1
    return brs_to_header == 0


def loop_has_single_br_in_header(natural_loop, cfg):
    (loop_blocks, _, header, _) = natural_loop
    num_brs = 0
    for instr in cfg[header][INSTRS]:
        if is_br(instr):
            num_brs += 1
    return num_brs == 1


def arg_is_constant(arg, cfg):
    """
    Returns the value of the arg is defined if the arg is defined as a integer
    constant exactly once in the cfg, otherwise returns false
    """
    num_defs = 0
    vals = []
    for basic_block in cfg:
        for instr in cfg[basic_block][INSTRS]:
            if is_const(instr) and get_dest(instr) == arg:
                num_defs += 1
                val = instr[VALUE]
                vals.append(val)
    if num_defs == 0 or num_defs >= 2:
        return False
    return vals[0]


def loop_has_one_iteration_var(natural_loop, cfg, domby):
    (loop_blocks, _, header, _) = natural_loop
    body_blocks = set(loop_blocks).difference({header})

    # find the (assumed) loop var, which is assumed to be in the branch condition of the header
    header_instrs = cfg[header][INSTRS]
    for i, header_instr in enumerate(header_instrs):
        if is_br(header_instr):
            cond_var = header_instr[ARGS][0]
            # backtrack to the definition of the cond variable, which should be a comparison defined in the header,
            # between an integer bound and the iteration variable
            # the iteration variable will not be defined inside the loop header
            # further, it will change somewhere in the loop body.
            # Thus, we have to consider both arguments in the comparison
            args = None
            comp_op = None
            for j, other_instr in enumerate(header_instrs):
                if j >= i:
                    break
                if not has_dest(other_instr):
                    continue
                dest = get_dest(other_instr)
                if dest != cond_var:
                    continue
                if not is_cmp(other_instr):
                    continue
                comp_op = other_instr[OP]
                args = get_args(other_instr)

            if args == None:
                return False

            assert len(args) == 2
            assert comp_op != None

            # have to figure out which of the args is the iteration variable!
            # To do so, we iterate over all Non-header blocks of the loop
            # We limit the iteration variable to only change once in the loop
            # via an increment/decrement operation, in which it is a singular argument
            # where the argument must be a static number, defined in the cfg (e.g. never changed in the cfg, defined as a constant once)
            # for now, we REQUIRE the incr/decr to be by 1!!!
            # The Other argument, the non iteration variable, must be defined as a constant once in the cfg
            # Should both args satisfy this, we cannot disambiguate, and bail by returning false
            final_args = []  # holds the arg names that could be iteration vars
            bump_val = []  # holds the amount an iteration var is bumped each time
            # whether the iteration var is bumped incrementally (true) or decrementally (false)
            is_incr = []
            cmp_op = []  # what type of comparison for the iteration var
            # what the non-iteration var's start value is (termination condition/ end val for the iteration var)
            end_val = []
            start_val = []  # what the iteration variable starts at
            for arg in args:
                for loop_block in loop_blocks:
                    if loop_block == header:
                        continue

                    for loop_instr in cfg[loop_block][INSTRS]:
                        if not has_dest(loop_instr):
                            continue
                        dst = get_dest(loop_instr)
                        if dst != arg:
                            continue
                        if not has_args(loop_instr):
                            continue
                        instr_args = get_args(loop_instr)
                        if arg not in instr_args:
                            continue
                        if set(instr_args) == set(arg):
                            continue
                        if not is_add(loop_instr) and not is_sub(loop_instr):
                            continue
                        remaining_arg = list(
                            set(instr_args).difference({arg}))[0]
                        remaining_arg_is_const = arg_is_constant(
                            remaining_arg, cfg)
                        if remaining_arg_is_const == False:
                            continue

                        other_arg = list(set(args).difference({arg}))[0]
                        other_arg_is_const = arg_is_constant(other_arg, cfg)
                        if type(other_arg_is_const) == bool and other_arg_is_const == False:
                            continue

                        if remaining_arg_is_const != 1:
                            continue

                        # Now we determine the start value for the iteration variable.
                        # We check the dominator tree, and check for the final constant assignment to the iteration variable
                        # before the loop header, strictly excluding the header itself
                        # thus we us strict dominators
                        strictly_dominating_blocks = get_strict_dominators(domby)[
                            header]
                        most_recent_const_assignment = None
                        for strict_dom_block in strictly_dominating_blocks:
                            for instr in cfg[strict_dom_block][INSTRS]:
                                if is_const(instr) and get_dest(instr) == arg:
                                    most_recent_const_assignment = instr
                        if most_recent_const_assignment == None:
                            continue

                        final_args.append(arg)
                        bump_val.append(remaining_arg_is_const)
                        is_incr.append(True if is_add(loop_instr) else False)
                        cmp_op.append(comp_op)
                        end_val.append(other_arg_is_const)
                        start_val.append(most_recent_const_assignment[VALUE])

            if len(final_args) == 0 or len(final_args) >= 2:
                return False

            assert 1 == len(final_args) == len(bump_val) == len(
                is_incr) == len(cmp_op) == len(end_val) == len(start_val)
            return FullyUnrollableLoop(header, body_blocks, final_args[0], start_val[0], bump_val[0], end_val[0], is_incr[0], cmp_op[0])

    # no branch found. Bail by returning False
    return False


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
                new_branch_instr = build_br(
                    instr[ARGS][0], new_branch_label, instr[LABELS][1])
            else:
                new_branch_instr = build_br(
                    instr[ARGS][0], instr[LABELS][0], new_branch_label)
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
            new_br = build_br(
                instr[ARGS][0], f"{instr[LABELS][0]}.{i}", f"{instr[LABELS][1]}.{i}")
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
    insert_into_cfg_w_blocks(UNROLLING_EMERGENCY_RET_LABEL, [
                             build_void_ret()], [], [], cfg)

    # start unrolling
    for loop in natural_loops:
        if not loop_has_single_exit(loop):
            continue
        if loop_is_nested(loop, natural_loops):
            continue

        (natural_loop, _, header, exits) = loop

        # insert UNROLL_FACTOR copies of headers and loop bodies into the cfg
        header_labels = []
        for i in range(UNROLL_FACTOR):
            new_header_name = gen_header_label(i)
            header_labels.append(new_header_name)
            for block in natural_loop:
                if block == header:
                    header_instrs = cfg[header][INSTRS]
                    if is_label(header_instrs[0]):
                        header_instrs = header_instrs[1:]
                    new_header_label = build_label(new_header_name)
                    insert_into_cfg_w_blocks(
                        new_header_name, [new_header_label] + deepcopy(header_instrs), [], [], cfg)
                else:
                    block_instrs = cfg[block][INSTRS]
                    new_block_instrs = renumber_loop_body_labels(
                        deepcopy(block_instrs), i, [header])
                    insert_into_cfg_w_blocks(
                        f"{block}.{i}", new_block_instrs, [], [], cfg)

        # enter unrolled loop headers and bodies, preds and succs
        loop_labels = []
        for block in natural_loop:
            if block != header:
                loop_labels.append(block)

        # Change preds and succs, modify the blocks as necessary
        # start with original header
        assert len(header_labels) != 0
        br_arg_index, loop_entry_label = get_br_index(
            cfg[header][INSTRS], header, exits)
        next_header = header_labels[0]
        modify_loop_jumps(loop_labels, cfg, header, next_header)

        original_header_succs = deepcopy(cfg[header][SUCCS])
        assert len(original_header_succs) == 2
        for loop_block_name in natural_loop:
            original_header_succs = set(
                original_header_succs).difference({loop_block_name})
        assert len(original_header_succs) == 1
        original_header_succs = list(original_header_succs)[0]
        cfg[header][SUCCS] = [header_labels[0]]

        prev_header = header
        for i in range(UNROLL_FACTOR - 1):
            current_header = header_labels[i]
            next_header = header_labels[i + 1]
            modify_header_branch(
                current_header, cfg, f"{loop_entry_label}.{i}", 1 if br_arg_index == 0 else 0)
            modified_loop_labels = []
            for label in loop_labels:
                new_label = f"{label}.{i}"
                modified_loop_labels.append(new_label)
            modify_loop_jumps(modified_loop_labels, cfg, header, next_header)
            # preds
            cfg[current_header][PREDS] = [prev_header]
            prev_header = current_header
            # succs
            cfg[current_header][SUCCS] = [next_header]

        i += 1
        # handle final unrolled loop header and body
        final_header = header_labels[i]
        modify_header_branch(
            final_header, cfg, f"{loop_entry_label}.{i}", 1 if br_arg_index == 0 else 0)
        modified_loop_labels = []
        for label in loop_labels:
            new_label = f"{label}.{i}"
            modified_loop_labels.append(new_label)

        # preds
        cfg[final_header][PREDS] = [prev_header]
        # succs
        cfg[final_header][SUCCS] = [original_header_succs]

        # fix up out of original loop preds
        cfg[original_header_succs][SUCCS] = [final_header]

    # DO JOINING ON CFG
    new_instrs = join_cfg(cfg)
    func[INSTRS] = new_instrs
    return func


def unroll_prog(prog):
    for func in prog[FUNCTIONS]:
        unroll_func(func)
    return prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = fully_unroll_prog(prog)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
