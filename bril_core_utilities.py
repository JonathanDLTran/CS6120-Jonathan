from bril_core_constants import *


def is_phi(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == PHI


def is_unop(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] in BRIL_UNOPS


def is_binop(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] in BRIL_BINOPS


def is_const(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == CONST


def is_id(instr):
    assert type(instr) == dict
    return OP in instr and instr[OP] == ID


def postorder_traversal(node, tree):
    assert node in tree
    postorder = []
    for child in tree[node]:
        postorder += postorder_traversal(child, tree)
    postorder.append(node)
    return postorder


def reverse_postorder_traversal(node, tree):
    return list(reversed(postorder_traversal(node, tree)))


def build_unop(unop, arg):
    pass


def build_binop(binop, arg1, arg2):
    pass
