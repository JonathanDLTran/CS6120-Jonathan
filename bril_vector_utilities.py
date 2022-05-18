from bril_vector_constants import *
from bril_core_constants import *


def is_vec(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] in VEC_OPS


def build_vecbinop(dest, left, right, binop):
    assert type(dest) == str
    assert type(left) == str
    assert type(right) == str
    assert binop in VEC_BINOPS
    return {DEST: dest, TYPE: VECTOR, OP: binop, ARGS: [left, right]}


def build_vecadd(dest, left, right):
    return build_vecbinop(dest, left, right, VECADD)


def build_vecsub(dest, left, right):
    return build_vecbinop(dest, left, right, VECSUB)


def build_vecmul(dest, left, right):
    return build_vecbinop(dest, left, right, VECMUL)


def build_vecdiv(dest, left, right):
    return build_vecbinop(dest, left, right, VECDIV)


def build_vecunop(dest, arg, unop):
    assert type(dest) == str
    assert type(arg) == str
    assert unop in VEC_UNOPS
    return {DEST: dest, TYPE: VECTOR, OP: unop, ARGS: [arg]}


def build_vecneg(dest, arg):
    return build_vecunop(dest, arg, VECNEG)


def build_vecmac(dest, m1, m2, a):
    assert type(dest) == str
    assert type(m1) == str
    assert type(m2) == str
    assert type(a) == str
    return {DEST: dest, TYPE: VECTOR, OP: VECMAC, ARGS: [m1, m2, a]}


def build_veczero(dest):
    assert type(dest) == str
    return {DEST: dest, TYPE: VECTOR, OP: VECZERO, ARGS: []}


def build_vecload(vector, index, data):
    assert type(vector) == str
    assert type(index) == str
    assert type(data) == str
    return {OP: VECLOAD, ARGS: [vector, index, data]}


def build_vecstore(dest, vector, index):
    assert type(vector) == str
    assert type(index) == str
    assert type(dest) == str
    return {DEST: dest, TYPE: VECTOR, OP: VECSTORE, ARGS: [vector, index]}
