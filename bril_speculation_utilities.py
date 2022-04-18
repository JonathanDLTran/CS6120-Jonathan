from bril_speculation_constants import *
from bril_core_constants import (OP, ARGS, LABELS)


def is_speculate(instr):
    return OP in instr and instr[OP] == SPECULATE


def is_commit(instr):
    return OP in instr and instr[OP] == COMMIT


def is_guard(instr):
    return OP in instr and instr[OP] == GUARD


def is_spec(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] in SPEC_OPS


def build_speculate():
    return {
        OP: SPECULATE
    }


def build_commit():
    return {
        OP: COMMIT
    }


def build_guard(cond_var, jump_loc):
    return {
        OP: GUARD,
        ARGS: [cond_var],
        LABELS: [jump_loc],
    }
