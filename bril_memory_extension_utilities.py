from bril_memory_extension_constants import *
from bril_core_constants import *


def is_alloc(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == ALLOC


def is_free(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == FREE


def is_store(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == STORE


def is_load(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == LOAD


def is_ptradd(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == PTRADD


def is_mem(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] in MEM_OPS


def is_ptr_type(instr):
    return TYPE in instr and PTR in instr[TYPE]


def build_alloc(dest, typ, arg):
    return {DEST: dest, TYPE: typ, OP: ALLOC, ARGS: [arg]}


def build_free(dest, typ, arg):
    return {OP: FREE, ARGS: [arg]}


def build_load(dest, typ, addr):
    return {DEST: dest, TYPE: typ, OP: LOAD, ARGS: [addr]}


def build_store(typ, addr, data):
    return {OP: STORE, ARGS: [addr, data]}


def build_ptradd(dest, typ, ptr, offset):
    return {DEST: dest, TYPE: typ, OP: PTRADD, ARGS: [ptr, offset]}


def has_mem_ops(prog):
    for func in prog[FUNCTIONS]:
        for instr in func[INSTRS]:
            if is_mem(instr):
                return True
    return False
