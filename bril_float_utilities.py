from bril_float_constants import *
from bril_core_constants import OP, TYPE


def is_float(instr):
    assert type(instr) == dict
    return (OP in instr and instr[OP] in FLOAT_OPS) or (TYPE in instr and instr[TYPE] == FLOAT)
