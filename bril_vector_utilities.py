from bril_vector_constants import *
from bril_core_constants import *

def is_vec(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] in VEC_OPS