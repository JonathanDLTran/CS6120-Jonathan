"""
Utilities for SLP Vectorization
"""

from bril_core_constants import *
from bril_core_utilities import *
from bril_memory_extension_utilities import is_store
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
    return is_add(instr) or is_sub(instr) or is_mul(instr) or is_div(instr)


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
            if instr_is_vectorizable(instr):
                vector_run.append(instr)
        # vectorizing a run
        else:
            last_instr = vector_run[-1]
            last_instr_op = last_instr[OP]
            if instr_is_vectorizable(instr):
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
    independent_sequences = build_independent_sequences(basic_block_instrs)
    sorted_independent_sequences = []
    for independent_seq in independent_sequences:
        # sort instructions in an indenpdent sequence  by the opp code
        # This produces adds | divs | muls | subs
        new_independent_seq = sorted(
            independent_seq, key=lambda instr: instr[OP])
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


def topological_sort():
    pass
