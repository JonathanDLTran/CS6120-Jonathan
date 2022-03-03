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


def lvn_value_is_const(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == CONST


def lvn_value_is_arg(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == ARGUMENT


def lvn_value_is_id(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == ID


def get_lvn_value(curr_lvn_num, var2value_num, expr2value_num):
    if curr_lvn_num in var2value_num:
        value_num = var2value_num[curr_lvn_num]
        for expr, val in expr2value_num.items():
            if val == value_num:
                return expr
        raise RuntimeError("Value not bound in expr2value_num.")
    else:
        raise RuntimeError("LVN Num must be in var2value_num dictionary.")


def interpret_lvn_value(lvn_value, var2value_num, expr2value_num):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    if lvn_value_is_const(lvn_value):
        return lvn_value
    elif lvn_value_is_arg(lvn_value):
        return lvn_value
    new_args = []
    for arg_lvn_num in lvn_value[1:]:
        try:
            arg_lvn_value = get_lvn_value(
                arg_lvn_num, var2value_num, expr2value_num)
        except:
            # cannot simplify
            return lvn_value
        new_args.append(interpret_lvn_value(
            arg_lvn_value, var2value_num, expr2value_num))
    all_constants = True
    for a in new_args:
        if not lvn_value_is_const(a):
            all_constants = False

    op = lvn_value[0]
    # we disallow semi interpreted expressions, e.g. (ADD, const 1, 3)
    if not all_constants:
        # However, there are some other algebraic simplications possible.
        if op == EQ:
            if lvn_value[1] == lvn_value[2]:
                return (CONST, True)
        elif op == LT:
            if lvn_value[1] == lvn_value[2]:
                return (CONST, False)
        elif op == GT:
            if lvn_value[1] == lvn_value[2]:
                return (CONST, False)
        elif op == LE:
            if lvn_value[1] == lvn_value[2]:
                return (CONST, True)
        elif op == GE:
            if lvn_value[1] == lvn_value[2]:
                return (CONST, True)
        return lvn_value

    if op == CONST:
        raise RuntimeError(
            f"Constants are the base case: should be returned earlier.")
    elif op == ID:
        assert len(new_args) == 1
        return new_args[0]
    elif op == CALL:
        # unfortunately have to treat as uninterpreted function
        return lvn_value
    elif op == NOT:
        assert len(new_args) == 1
        (_, result) = new_args[0]
        return (CONST, not result)
    elif op == AND:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 and result2)
    elif op == OR:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 or result2)
    elif op == EQ:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 == result2)
    elif op == LE:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 <= result2)
    elif op == GE:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 >= result2)
    elif op == LT:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 < result2)
    elif op == GT:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 > result2)
    elif op == ADD:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 + result2)
    elif op == SUB:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 - result2)
    elif op == MUL:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        return (CONST, result1 * result2)
    elif op == DIV:
        assert len(new_args) == 2
        (_, result1, _) = new_args[0]
        (_, result2, _) = new_args[1]
        # bail on interpretation if divisor is 0
        if result2 == 0:
            return lvn_value
        return (CONST, result1 // result2)
    raise RuntimeError(f"LVN Interpretation: Unmatched type {op}.")
