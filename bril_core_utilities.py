from bril_core_constants import *


def is_phi(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == PHI


def build_unop(unop, arg):
    pass


def build_binop(binop, arg1, arg2):
    pass
