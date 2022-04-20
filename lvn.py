import click
from copy import deepcopy
import sys
import json
from bril_speculation_utilities import is_guard


from cfg import form_blocks, join_blocks
from bril_core_constants import *


LVN_NUMBER = 0
VARIABLE_NUMBER = 0


ARG_LVN_VALUE = "arg-value"
PREV_DEFINED_VAR = "prev-defined-var"


def gen_fresh_lvn_num():
    global LVN_NUMBER
    LVN_NUMBER += 1
    return LVN_NUMBER


def gen_fresh_variable(var):
    global VARIABLE_NUMBER
    VARIABLE_NUMBER += 1
    return f"{var}_{VARIABLE_NUMBER}"


def arg_to_lvn_value(arg, var_to_num, num_value_loc):
    if arg in var_to_num:
        return var_to_num[arg]
    new_num = gen_fresh_lvn_num()
    num_value_loc.append((new_num, (PREV_DEFINED_VAR, arg), arg))
    var_to_num[arg] = new_num
    return new_num


def lvn_value_is_const(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == CONST


def lvn_value_is_arg(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == ARG_LVN_VALUE


def lvn_value_is_prev_defined(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == PREV_DEFINED_VAR


def lvn_value_is_id(lvn_value):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    return lvn_value[0] == ID


def interpret_lvn_value(lvn_value, num_value_loc):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    if lvn_value_is_const(lvn_value):
        return lvn_value
    elif lvn_value_is_arg(lvn_value):
        return lvn_value
    elif lvn_value_is_prev_defined(lvn_value):
        return lvn_value
    new_args = []
    for arg_lvn_num in lvn_value[1:]:
        arg_lvn_value = get_lvn_value(arg_lvn_num, num_value_loc)
        new_args.append(interpret_lvn_value(arg_lvn_value, num_value_loc))
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
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 and result2)
    elif op == OR:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 or result2)
    elif op == EQ:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 == result2)
    elif op == LE:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 <= result2)
    elif op == GE:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 >= result2)
    elif op == LT:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 < result2)
    elif op == GT:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 > result2)
    elif op == ADD:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 + result2)
    elif op == SUB:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 - result2)
    elif op == MUL:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        return (CONST, result1 * result2)
    elif op == DIV:
        assert len(new_args) == 2
        (_, result1) = new_args[0]
        (_, result2) = new_args[1]
        # bail on interpretation if divisor is 0
        if result2 == 0:
            return lvn_value
        return (CONST, result1 // result2)
    raise RuntimeError(f"LVN Interpretation: Unmatched type {op}.")


def instr_to_lvn_value(instr, var_to_num, num_value_loc):
    if OP in instr and instr[OP] == CONST:
        return (CONST, instr[VALUE])
    elif OP in instr and instr[OP] in BRIL_BINOPS + BRIL_UNOPS:
        args = instr[ARGS]
        if instr[OP] in BRIL_COMMUTE_BINOPS:
            args = sorted(args)
        return interpret_lvn_value((instr[OP], *list(map(lambda a: arg_to_lvn_value(a, var_to_num, num_value_loc), args))), num_value_loc)
    elif OP in instr and instr[OP] in [CALL]:
        return interpret_lvn_value((CALL, *list(map(lambda a: arg_to_lvn_value(a, var_to_num, num_value_loc), instr[ARGS]))), num_value_loc)
    elif OP in instr and instr[OP] in [ID]:
        return interpret_lvn_value((ID, *list(map(lambda a: arg_to_lvn_value(a, var_to_num, num_value_loc), instr[ARGS]))), num_value_loc)
    raise RuntimeError(f"Requires Instruction to Assign to Variable\n{instr}.")


def get_canonical_loc(curr_lvn_num, num_value_loc):
    for (lvn_num, _, canonical_loc) in num_value_loc:
        if lvn_num == curr_lvn_num:
            return canonical_loc
    else:
        raise RuntimeError("LVN Num must be in num_value_loc table.")


def get_lvn_value(curr_lvn_num, num_value_loc):
    for (lvn_num, lvn_value, _) in num_value_loc:
        if lvn_num == curr_lvn_num:
            return lvn_value
    else:
        raise RuntimeError("LVN Num must be in num_value_loc table.")


def lvn_value_to_instr(dst, lvn_value, num_value_loc, original_instr):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    first = lvn_value[0]
    if first == CONST:
        assert len(lvn_value) == 2
        return {DEST: dst, OP: CONST, TYPE: INT, VALUE: lvn_value[1]}
    elif first in [ADD, SUB, MUL, DIV]:
        assert len(lvn_value) == 3
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        arg2 = get_canonical_loc(lvn_value[2], num_value_loc)
        return {DEST: dst, OP: first, TYPE: INT, ARGS: [arg1, arg2]}
    elif first in [EQ, LT, GT, LE, GE, AND, OR]:
        assert len(lvn_value) == 3
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        arg2 = get_canonical_loc(lvn_value[2], num_value_loc)
        return {DEST: dst, OP: first, TYPE: BOOL, ARGS: [arg1, arg2]}
    elif first in [NOT]:
        assert len(lvn_value) == 2
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        return {DEST: dst, OP: NOT, TYPE: BOOL, ARGS: [arg1]}
    elif first in [CALL]:
        assert len(lvn_value) >= 2
        args = list(map(lambda a: get_canonical_loc(
            a, num_value_loc), lvn_value[1:]))
        return {DEST: dst, OP: CALL, ARGS: args, FUNCS: original_instr[FUNCS], TYPE: original_instr[TYPE]}
    elif first in [ID]:
        assert len(lvn_value) == 2
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        return {DEST: dst, OP: ID, ARGS: [arg1]}
    else:
        raise RuntimeError(f"Unmatched LVN Value type {lvn_value}")


def lvn_value_equality(lvn_val1, lvn_val2, num_value_loc):
    assert type(lvn_val1) == tuple and len(lvn_val1) >= 2
    assert type(lvn_val2) == tuple and len(lvn_val2) >= 2
    if lvn_val1 == lvn_val2:
        return True
    # Do Algebraic Simplication
    op1 = lvn_val1[0]
    op2 = lvn_val2[0]
    if op1 == ADD and op2 == MUL:
        if lvn_val1[1] == lvn_val1[2] and lvn_val2[1] == lvn_val1[1] and get_lvn_value(lvn_val2[2], num_value_loc) == (CONST, 2):
            return True
        elif lvn_val1[1] == lvn_val1[2] and lvn_val2[2] == lvn_val1[1] and get_lvn_value(lvn_val2[1], num_value_loc) == (CONST, 2):
            return True
    elif op1 == MUL and op2 == ADD:
        if lvn_val2[1] == lvn_val2[2] and lvn_val1[1] == lvn_val2[1] and get_lvn_value(lvn_val1[2], num_value_loc) == (CONST, 2):
            return True
        elif lvn_val2[1] == lvn_val2[2] and lvn_val1[2] == lvn_val2[1] and get_lvn_value(lvn_val1[1], num_value_loc) == (CONST, 2):
            return True
    return False


def instr_lvn(instr, remainder_bb, var_to_num, num_value_loc):
    if DEST in instr:
        dst_var = instr[DEST]
        new_lvn_val = instr_to_lvn_value(instr, var_to_num, num_value_loc)

        in_lvn_table = False
        in_lvn_table_num = None
        for (lvn_num, lvn_val, _) in num_value_loc:
            if lvn_value_equality(lvn_val, new_lvn_val, num_value_loc):
                in_lvn_table = True
                in_lvn_table_num = lvn_num
                break

        # copy propagation shortcut
        if lvn_value_is_id(new_lvn_val):
            assert len(new_lvn_val) == 2
            lvn_table_num = new_lvn_val[1]
            var_to_num[dst_var] = lvn_table_num
            arg = get_canonical_loc(lvn_table_num, num_value_loc)
            return {DEST: dst_var, OP: ID, TYPE: instr[TYPE], ARGS: [arg]}
        elif in_lvn_table:
            assert in_lvn_table_num != None
            var_to_num[dst_var] = in_lvn_table_num
            # constant propagation shortcut:
            if lvn_value_is_const(new_lvn_val):
                return {DEST: dst_var, OP: CONST, TYPE: instr[TYPE], VALUE: new_lvn_val[1]}
            return {DEST: dst_var, OP: ID, TYPE: instr[TYPE], ARGS: [get_canonical_loc(in_lvn_table_num, num_value_loc)]}
        else:
            new_lvn_num = gen_fresh_lvn_num()

            # consider that the variable will get rewritten
            dest_overwritten = False
            for rem_instr in remainder_bb:
                if DEST in rem_instr and rem_instr[DEST] == dst_var:
                    dest_overwritten = True
                    break
            if dest_overwritten:
                new_dst_var = gen_fresh_variable(dst_var)
                row_triple = (new_lvn_num, new_lvn_val, new_dst_var)
                num_value_loc.append(row_triple)
                # keep mapping with old destination variable
                var_to_num[dst_var] = new_lvn_num
                # but replace instruction with new variable as that is the canonical location
                return lvn_value_to_instr(new_dst_var, new_lvn_val, num_value_loc, instr)
            else:
                row_triple = (new_lvn_num, new_lvn_val, dst_var)
                num_value_loc.append(row_triple)
                var_to_num[dst_var] = new_lvn_num
                return lvn_value_to_instr(dst_var, new_lvn_val, num_value_loc, instr)
    else:
        if (ARGS in instr and LABELS not in instr) or is_guard(instr):
            new_instr = deepcopy(instr)
            new_instr_args = []
            for a in instr[ARGS]:
                if a not in var_to_num:
                    new_instr_args.append(a)
                else:
                    new_instr_args.append(get_canonical_loc(
                        var_to_num[a], num_value_loc))
            new_instr[ARGS] = new_instr_args
            return new_instr
        else:
            return instr


def lvn(program):
    for func in program["functions"]:
        basic_blocks = form_blocks(func["instrs"])
        new_basic_blocks = []
        for bb in basic_blocks:
            new_bb = []
            var_to_num = {}
            num_value_loc = []
            if ARGS in func:
                for i, arg_dict in enumerate(func[ARGS]):
                    arg = arg_dict["name"]
                    new_arg_lvn_num = gen_fresh_lvn_num()
                    new_row = (new_arg_lvn_num, (ARG_LVN_VALUE, arg), arg)
                    var_to_num[arg] = new_arg_lvn_num
                    num_value_loc.append(new_row)
            for i, instr in enumerate(bb):
                remainder_bb = bb[i + 1:]
                new_instr = instr_lvn(
                    instr, remainder_bb, var_to_num, num_value_loc)
                new_bb.append(new_instr)
            new_basic_blocks.append(new_bb)
        func["instrs"] = join_blocks(new_basic_blocks)
    return program


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = lvn(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
