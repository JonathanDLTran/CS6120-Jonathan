from bril_speculation_constants import *
from bril_core_constants import OP


def is_speculate(instr):
    return OP in instr and instr[OP] == SPECULATE


def is_commit(instr):
    return OP in instr and instr[OP] == COMMIT


def is_guard(instr):
    return OP in instr and instr[OP] == GUARD
