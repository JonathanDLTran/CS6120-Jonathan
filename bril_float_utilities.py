from bril_float_constants import *
from bril_core_constants import FUNCTIONS, INSTRS, OP, TYPE, DEST, ARGS


def is_float(instr):
    assert type(instr) == dict
    return (OP in instr and instr[OP] in FLOAT_OPS) or (TYPE in instr and instr[TYPE] == FLOAT)


def is_float_op(instr, op):
    assert type(instr) == dict
    return OP in instr and instr[OP] == op


def is_fadd(instr):
    return is_float_op(instr, FADD)


def is_fsub(instr):
    return is_float_op(instr, FSUB)


def is_fmul(instr):
    return is_float_op(instr, FMUL)


def is_fdiv(instr):
    return is_float_op(instr, FDIV)


def build_float_binop(dest, op, arg1, arg2):
    return {DEST: dest, TYPE: FLOAT, OP: op, ARGS: [arg1, arg2]}


def build_fadd(dest, arg1, arg2):
    return build_float_binop(dest, FADD, arg1, arg2)


def build_fsub(dest, arg1, arg2):
    return build_float_binop(dest, FSUB, arg1, arg2)


def build_fmul(dest, arg1, arg2):
    return build_float_binop(dest, FMUL, arg1, arg2)


def build_fdiv(dest, arg1, arg2):
    return build_float_binop(dest, FDIV, arg1, arg2)


def has_float_ops(prog):
    for func in prog[FUNCTIONS]:
        for instr in func[INSTRS]:
            if is_float(instr):
                return True
    return False
