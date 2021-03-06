"""
Utilities for SLP Vectorization
"""

from bril_core_constants import *
from bril_core_utilities import *
from bril_memory_extension_utilities import is_ptradd, is_store
from bril_vector_constants import *
from cfg import form_cfg_w_blocks, join_cfg


OP_TO_VECOP = {
    ADD: VECADD, SUB: VECSUB, MUL: VECMUL, DIV: VECDIV,
}

NEW_VECTOR_VAR = "new_vector_var"
NEW_VECTOR_VAR_IDX = 0
NEW_VECTOR_IDX = "new_vector_idx"
NEW_VECTOR_IDX_IDX = 0
NEW_VECTOR_ONE = "one"
NEW_VECTOR_ONE_IDX = 0
RESULT_VECTOR_VAR = "result_vector_var"
RESULT_VECTOR_VAR_IDX = 0
NEW_VECTOR_CONST = "vec_const"
NEW_VECTOR_CONST_IDX = 0


RUN_THRESHOLD = 2


def gen_new_vector_var():
    global NEW_VECTOR_VAR_IDX
    NEW_VECTOR_VAR_IDX += 1
    return f"{NEW_VECTOR_VAR}_{NEW_VECTOR_VAR_IDX}"


def gen_new_vector_idx():
    global NEW_VECTOR_IDX_IDX
    NEW_VECTOR_IDX_IDX += 1
    return f"{NEW_VECTOR_IDX}_{NEW_VECTOR_IDX_IDX}"


def gen_new_vector_one():
    global NEW_VECTOR_ONE_IDX
    NEW_VECTOR_ONE_IDX += 1
    return f"{NEW_VECTOR_ONE}_{NEW_VECTOR_ONE_IDX}"


def gen_result_vector_var():
    global RESULT_VECTOR_VAR_IDX
    RESULT_VECTOR_VAR_IDX += 1
    return f"{RESULT_VECTOR_VAR}_{RESULT_VECTOR_VAR_IDX}"


def gen_new_vector_const():
    global NEW_VECTOR_CONST_IDX
    NEW_VECTOR_CONST_IDX += 1
    return f"{NEW_VECTOR_CONST}_{NEW_VECTOR_CONST_IDX}"


def is_homogenous(instrs):
    """
    True of all instructions are of the same OPeration, e.g. all multiplications
    """
    assert len(instrs) > 0
    assert OP in instrs[0]
    first_op = instrs[0][OP]
    for instr in instrs:
        if instr[OP] != first_op:
            return False
    return True


def is_independent(instrs):
    """
    True if all instructions independent from each other
    """
    assert len(instrs) > 0
    for i, instr in enumerate(instrs[1:]):
        for prev_instr in instrs[:i]:
            assert ARGS in instr
            assert DEST in prev_instr
            if prev_instr[DEST] in instr[ARGS]:
                return False
    return True


def instr_is_vectorizable(instr):
    # Division is not necesarily vectorizable, because partially packing and then dividing will cause division by 0
    return is_add(instr) or is_sub(instr) or is_mul(instr)


def instr_is_vectorizable_w_div(instr):
    return is_add(instr) or is_sub(instr) or is_mul(instr) or is_div(instr)


def filter_runs(runs, threshold):
    filted_runs = []
    for run in runs:
        if len(run) >= threshold:
            filted_runs.append(run)
    return filted_runs


def instr_used(vector_run, instr):
    """
    True if instr uses as any of its arguments any variable defined for an instruction in vector run
    """
    if ARGS not in instr:
        return False
    for past_instr in vector_run:
        assert DEST in past_instr
        if past_instr[DEST] in instr[ARGS]:
            return True
    return False


def build_runs(basic_block_instrs):
    runs = []
    vector_run = []
    for instr in basic_block_instrs:
        # not yet begun vectorizing a run
        if vector_run == []:
            if instr_is_vectorizable(instr):
                vector_run.append(instr)
        # vectorizing a run
        else:
            last_instr = vector_run[-1]
            last_instr_op = last_instr[OP]
            if instr_is_vectorizable(instr) and last_instr_op != instr[OP]:
                runs.append(vector_run)
                vector_run = []
            elif instr_used(vector_run, instr):
                runs.append(vector_run)
                vector_run = []
            elif is_store(instr):
                runs.append(vector_run)
                vector_run = []
            elif len(vector_run) == VECTOR_LANE_WIDTH:
                runs.append(vector_run)
                vector_run = []

            # otherwise check if still vectorizable and add
            if instr_is_vectorizable(instr):
                vector_run.append(instr)
            else:
                if vector_run != []:
                    runs.append(vector_run)
                vector_run = []

    if vector_run != []:
        runs.append(vector_run)

    return runs


def build_independent_sequences(basic_block_instrs):
    """
    Like Build Runs, but disregard the type of isntruction
    Used as a helper for canoncailize basic block
    """
    runs = []
    vector_run = []
    for instr in basic_block_instrs:
        # not yet begun vectorizing a run
        if vector_run == []:
            if instr_is_vectorizable_w_div(instr):
                vector_run.append(instr)
        # vectorizing a run
        else:
            if instr_used(vector_run, instr):
                runs.append(vector_run)
                vector_run = []
            elif is_store(instr):
                runs.append(vector_run)
                vector_run = []

            # otherwise check if still vectorizable and add
            if instr_is_vectorizable_w_div(instr):
                vector_run.append(instr)
            else:
                if vector_run != []:
                    runs.append(vector_run)
                vector_run = []

    if vector_run != []:
        runs.append(vector_run)

    return runs


def last_instrs_of_runs(runs):
    """
    Grab the last instructions of every run
    """
    last_instrs = dict()
    for i, run in enumerate(runs):
        assert len(run) > 0
        last_instrs[id(run[-1])] = i
    return last_instrs


def all_instrs_in_runs(runs):
    all_instrs = set()
    for run in runs:
        for instr in run:
            all_instrs.add(id(instr))
    return all_instrs


def canonicalize_basic_block(basic_block_instrs):
    """
    For each set of independent instructions, move the set of instructions
    into adds, subs, muls and divs, separated, so that we can take advantage
    of these runs.
    """
    ALPHABETICALLY_FIRST = "AAAAAAA"

    def division_sorting(instr):
        op = instr[OP]
        if op == DIV:
            return ALPHABETICALLY_FIRST
        return op

    independent_sequences = build_independent_sequences(basic_block_instrs)
    sorted_independent_sequences = []
    for independent_seq in independent_sequences:
        # sort instructions in an indenpdent sequence  by the opp code
        # This produces adds | divs | muls | subs
        new_independent_seq = sorted(
            independent_seq, key=division_sorting)
        sorted_independent_sequences.append(new_independent_seq)

    # begin stitching together the basic block with new sorted instructions
    # grab last instruction of every run
    last_instrs_map = last_instrs_of_runs(independent_sequences)

    # grab all instrucitons in runs
    all_instrs_of_runs = all_instrs_in_runs(independent_sequences)

    # build the new basic block
    sorted_basic_block_instrs = []
    # insert the new packed instructions for every run
    for instr in basic_block_instrs:
        instr_id = id(instr)
        if instr_id in last_instrs_map:
            run_idx = last_instrs_map[instr_id]
            sorted_basic_block_instrs += sorted_independent_sequences[run_idx]
        elif instr_id in all_instrs_of_runs:
            pass
        else:
            sorted_basic_block_instrs.append(instr)

    return sorted_basic_block_instrs


def canonicalize_func(func):
    cfg = form_cfg_w_blocks(func)
    for basic_block in cfg:
        new_instrs = canonicalize_basic_block(
            cfg[basic_block][INSTRS])
        cfg[basic_block][INSTRS] = new_instrs

    final_instrs = join_cfg(cfg)
    func[INSTRS] = final_instrs
    return func


def canonicalize_prog(prog):
    for func in prog[FUNCTIONS]:
        canonicalize_func(func)
    return prog


def forward_movement_basic_block(basic_block_instrs, is_instr_func):
    # cannot generally reorder calls
    assert is_instr_func != is_call
    new_basic_block = []
    for instr in basic_block_instrs:
        # add all non instructions of interest to the new basic block
        if not is_instr_func(instr):
            new_basic_block.append(instr)
            continue

        # when the basic block still has instructions
        collector = []
        while new_basic_block != []:
            last_instr = new_basic_block.pop()
            # do not move before a label or a phi instruction
            if is_label(last_instr) or is_phi(last_instr):
                new_basic_block.append(last_instr)
                break

            # do not move before a call instruction
            if is_instr_func == is_print and is_call(last_instr):
                new_basic_block.append(last_instr)
                break

            # do not reorder prints
            if is_instr_func == is_print and is_print(last_instr):
                new_basic_block.append(last_instr)
                break

            instr_dest = None
            if DEST in instr:
                instr_dest = instr[DEST]

            if ARGS in last_instr:
                last_instr_uses = last_instr[ARGS]
                # cannot swap instruction and prior instruction due to a write-read conflict
                if instr_dest != None and instr_dest in last_instr_uses:
                    new_basic_block.append(last_instr)
                    break

            if DEST in last_instr:
                last_instr_dest = last_instr[DEST]
                # do not swap order of definitions (write-write conflict)
                if instr_dest != None and last_instr_dest == instr_dest:
                    new_basic_block.append(last_instr)
                    break
                # do not swap a read-write conflict
                elif ARGS in instr:
                    instr_args = instr[ARGS]
                    if last_instr_dest in instr_args:
                        new_basic_block.append(last_instr)
                        break

            # instruction can swap before last instruction
            collector.append(last_instr)

        # add the instruction of interest
        new_basic_block.append(instr)
        new_basic_block += list(reversed(collector))

    return new_basic_block


def backward_movement_basic_block(basic_block_instrs, is_instr_func):
    # cannot generally reorder calls
    assert is_instr_func != is_call

    # begin by storing new instruction order in reverse order
    # instructions closer to the front are in later in the basic block
    new_basic_block = []
    for instr in reversed(basic_block_instrs):
        if not is_instr_func(instr):
            new_basic_block.append(instr)
            continue

        collector = []
        while new_basic_block != []:
            last_instr = new_basic_block.pop()
            # do not move before a terminator instruction
            if is_terminator(last_instr):
                new_basic_block.append(last_instr)
                break

            # do not move before a call instruction
            if is_call(last_instr):
                new_basic_block.append(last_instr)
                break

            # do not reorder prints
            if is_print(last_instr):
                new_basic_block.append(last_instr)
                break

            instr_dest = None
            if DEST in instr:
                instr_dest = instr[DEST]

            if ARGS in last_instr:
                last_instr_uses = last_instr[ARGS]
                # cannot swap instruction and prior instruction due to a write-read conflict
                if instr_dest != None and instr_dest in last_instr_uses:
                    new_basic_block.append(last_instr)
                    break

            if DEST in last_instr:
                last_instr_dest = last_instr[DEST]
                # do not swap order of definitions (write-write conflict)
                if instr_dest != None and last_instr_dest == instr_dest:
                    new_basic_block.append(last_instr)
                    break
                # do not swap a read-write conflict
                elif ARGS in instr:
                    instr_args = instr[ARGS]
                    if last_instr_dest in instr_args:
                        new_basic_block.append(last_instr)
                        break

            # instruction can swap before last instruction
            collector.append(last_instr)

        new_basic_block.append(instr)
        new_basic_block += list(reversed(collector))

    # finish by changing to un-reversed order
    new_basic_block = list(reversed(new_basic_block))
    return new_basic_block


def movement_function(func, basic_block_movement_func, is_instr_func):
    cfg = form_cfg_w_blocks(func)
    for basic_block in cfg:
        new_instrs = basic_block_movement_func(
            cfg[basic_block][INSTRS], is_instr_func)
        cfg[basic_block][INSTRS] = new_instrs

    final_instrs = join_cfg(cfg)
    func[INSTRS] = final_instrs
    return func


def movement_prog(prog, basic_block_movement_func, is_instr_func):
    for func in prog[FUNCTIONS]:
        movement_function(func, basic_block_movement_func, is_instr_func)
    return prog


def constant_movement(prog):
    """
    Move constant definitions as early as possible in basic blocks
    to allow for greater vectorization potential
    """
    return movement_prog(prog, forward_movement_basic_block, is_const)


def id_movement(prog):
    """
    Move IDS as early as possible
    """
    return movement_prog(prog, forward_movement_basic_block, is_id)


def print_movement(prog):
    """
    Move Prints as late as possible
    """
    return movement_prog(prog, backward_movement_basic_block, is_print)
