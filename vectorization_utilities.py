"""
Utilities for SLP Vectorization
"""

from bril_core_constants import *
from bril_core_utilities import *
from bril_vector_constants import *


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


def topological_sort():
    pass
