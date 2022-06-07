"""
The point of LVN is to "disentangle" variables and the values behind each variable.

We build 2 data structures:
A table with LVN Number - LVN Value - Variable Home
and a map from Variable to LVN Number

is (Print, arg) a value number? Actually, a value number should be anything that is assigned,
and this is not. You could make a psuedo assignment to a variable called _ though.But this is probably
not the best result, as you can't replace a (print, arg) with another variable! the side effect
is that the print actually occurs, not that an assignment occurs.

Key idea is that one may want to track "block vars", e.g. incoming args, or vars defined in a prior basic block
and then make sure appropriate actions are occuring with the lvn values for these block vars

Maybe assign a block var (Arg, _) lvn value as appropriate at the location where an block var is used
and also create an id instruction for renaming purposes.

The idea is similar to Issue 77 on Bril
I will need to create copies before uses of a Block variable, including arguments.

Here, the scheme is that whenever a block variable gets overriden, then there must be an extra assignment meade

The invariant is that at the beginning and end of the block, each variable has its original name
"""


import click
from copy import deepcopy
import sys
import json

from collections import OrderedDict
from bril_core_utilities import build_id, commutes


from bril_speculation_utilities import is_guard


from cfg import form_cfg_w_blocks, join_cfg
from bril_core_constants import *


LVN_NUMBER = -1
VARIABLE_NUMBER = -1


def reset_lvn_num():
    global LVN_NUMBER
    LVN_NUMBER = -1


def gen_fresh_lvn_num():
    global LVN_NUMBER
    LVN_NUMBER += 1
    return LVN_NUMBER


def gen_fresh_variable(var):
    global VARIABLE_NUMBER
    VARIABLE_NUMBER += 1
    return f"{var}_{VARIABLE_NUMBER}_lvn"


ARG_LVN_VALUE = "arg-value"
PREV_DEFINED_VAR = "prev-defined-var"


BLOCK_VAR = "Block Var"


class Interpretable_values(object):
    def __init__(self) -> None: raise RuntimeError("Unimplemented")
    def is_interpretable(self): raise RuntimeError("Unimplemented")

    def __repr__(self) -> str:
        return self.__str__()

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)


class Lvn_number(Interpretable_values):
    def __init__(self, num) -> None:
        assert type(num) == int
        self.num = num

    def is_interpretable(self): return False

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Lvn_number):
            return False
        return self.num == __o.num

    def __str__(self) -> str:
        return f"(LVN Num {self.num})"


class Constant(Interpretable_values):
    def __init__(self, val) -> None:
        assert type(val) == int
        self.val = val

    def is_interpretable(self): return True

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Constant):
            return False
        return self.val == __o.val

    def __str__(self) -> str:
        return f"(Constant {self.val})"


class Lvn_value(object):
    def __init__(self, instr, var2num) -> None:
        assert DEST in instr
        assert ARGS in instr or VALUE in instr
        assert TYPE in instr
        assert OP in instr

        self.op = instr[OP]
        self.args = []
        if VALUE in instr:
            self.args.append(Constant(instr[VALUE]))
        elif ARGS in instr:
            for arg in instr[ARGS]:
                self.args.append(Lvn_number(var2num[arg]))
        else:
            raise RuntimeError(
                f"Match Failure for Arguments of Instruction: {instr}.")
        self.typ = instr[TYPE]
        self.dest = instr[DEST]

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Lvn_value):
            return False
        return self.op == __o.op and self.args == __o.args and self.typ == __o.typ and self.dest == __o.typ

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)

    def __str__(self) -> str:
        return f"({self.op}, {', '.join(self.args)})"

    def __repr__(self) -> str:
        return self.__str__()


def lvn_value_to_instr(dst, lvn_value, table, original_instr):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2
    first = lvn_value[0]
    if first == CONST:
        assert len(lvn_value) == 2
        return {DEST: dst, OP: CONST, TYPE: INT, VALUE: lvn_value[1]}
    elif first in [ADD, SUB, MUL, DIV]:
        assert len(lvn_value) == 3
        arg1 = get_from_table(table, lvn_value[1])[1]
        arg2 = get_from_table(table, lvn_value[2])[1]
        return {DEST: dst, OP: first, TYPE: INT, ARGS: [arg1, arg2]}
    elif first in [EQ, LT, GT, LE, GE, AND, OR]:
        assert len(lvn_value) == 3
        arg1 = get_from_table(table, lvn_value[1])[1]
        arg2 = get_from_table(table, lvn_value[2])[1]
        return {DEST: dst, OP: first, TYPE: BOOL, ARGS: [arg1, arg2]}
    elif first in [NOT]:
        assert len(lvn_value) == 2
        arg1 = get_from_table(table, lvn_value[1])[1]
        return {DEST: dst, OP: NOT, TYPE: BOOL, ARGS: [arg1]}
    elif first in [CALL]:
        assert len(lvn_value) >= 2
        args = list(map(lambda a: get_from_table(table, a)[1], lvn_value[1:]))
        return {DEST: dst, OP: CALL, ARGS: args, FUNCS: original_instr[FUNCS], TYPE: original_instr[TYPE]}
    elif first in [ID]:
        assert len(lvn_value) == 2
        arg1 = get_from_table(table, lvn_value[1])[1]
        return {DEST: dst, OP: ID, ARGS: [arg1]}
    else:
        raise RuntimeError(f"Unmatched LVN Value type {lvn_value}")


def lvn_value_is_const(lvn_value):
    assert type(lvn_value) == tuple
    return lvn_value[0] == CONST


def lvn_value_is_block_var(lvn_value):
    assert type(lvn_value) == tuple
    return lvn_value[0][:len(BLOCK_VAR)] == BLOCK_VAR


def lvn_value_is_id(lvn_value):
    assert type(lvn_value) == tuple
    return lvn_value[0] == ID


def interpret_lvn_value(lvn_value, table):
    assert type(lvn_value) == tuple
    if lvn_value_is_const(lvn_value):
        return lvn_value
    elif lvn_value_is_block_var(lvn_value):
        return lvn_value
    new_args = []
    for arg_lvn_num in lvn_value[1:]:
        arg_lvn_value = get_value_from_table(table, arg_lvn_num)
        new_args.append(interpret_lvn_value(arg_lvn_value, table))
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


def instr_to_lvn_value(instr, var2num, table):
    assert type(instr) == dict
    assert OP in instr

    args = []
    if ARGS in instr:
        # basic commutativity for algebraic identity
        if commutes(instr):
            args = sorted(instr[ARGS])
        else:
            args = instr[ARGS]
        args = list(map(lambda a: var2num[a], args))
    else:
        args = [instr[VALUE]]

    lvn_value = (instr[OP], *args)
    final_lvn_value = interpret_lvn_value(lvn_value, table)

    has_changed = lvn_value != final_lvn_value
    return final_lvn_value, has_changed


def get_var_types(func):
    """
    Build map from vars to typs in a function
    """
    var2typ = dict()

    # get args
    if ARGS in func:
        for arg in func[ARGS]:
            name = arg[NAME]
            typ = arg[TYPE]
            var2typ[name] = typ

    # get regular instructions
    for instr in func[INSTRS]:
        if DEST in instr:
            dst = instr[DEST]
            typ = instr[TYPE]
            var2typ[dst] = typ

    return var2typ


def add_instr_to_basic_block_front(instr, instrs):
    """
    APPLY ONLY if instrs contains at least one defintion to old_var_name
    """
    instrs.insert(0, instr)


def rename_vars(old_var_name, new_var_name, instrs):
    """
    Renames beginning instances of old_var_name in bb_instrs with new_var_names
    by changing all uses of old var name to new var name, BUT only before
    a definition to new_var_name

    ONLY APPLY BEFORE add_instr_to_basic_block_front
    AND ONLY if instrs contains at least one defintion to old_var_name
    """
    has_old_var_def = False
    for instr in instrs:
        if DEST in instr and instr[DEST] == old_var_name:
            has_old_var_def = True
    assert has_old_var_def

    new_instrs = []
    has_defined_old_var_name = False
    for instr in instrs:
        if has_defined_old_var_name:
            new_instrs.append(instr)
            continue

        new_instr = deepcopy(instr)
        # rename args first
        if ARGS in instr:
            new_args = []
            for a in instr[ARGS]:
                if a == old_var_name:
                    new_args.append(new_var_name)
                else:
                    new_args.append(a)
            new_instr[ARGS] = new_args
        # then consider destination
        if DEST in instr and instr[DEST] == old_var_name:
            has_defined_old_var_name = True
        new_instrs.append(new_instr)


def get_block_vars(instrs):
    """
    Grab all variables that are not defined with the basic block
    """
    defined_vars = set()
    block_vars = []
    for instr in instrs:
        # check args first
        if ARGS in instr:
            for a in instr[ARGS]:
                if a not in defined_vars:
                    block_vars.append(a)
        # then check dest
        if DEST in instr:
            dst = instr[DEST]
            defined_vars.add(dst)
    return block_vars


def handle_block_vars(instrs, var2typ):
    """
    Insert necesary instructions if block vars exist in basic blocks
    """
    block_vars = get_block_vars(instrs)

    n_inserts = 0
    updated_block_vars = set()
    for old_var_name in block_vars:

        has_old_var_def = False
        for instr in instrs:
            if DEST in instr and instr[DEST] == old_var_name:
                has_old_var_def = True

        if has_old_var_def:
            n_inserts += 1
            updated_block_vars.add(old_var_name)

            new_var_name = gen_fresh_variable(old_var_name)
            rename_vars(old_var_name, new_var_name, instrs)
            assert old_var_name in var2typ
            new_id_instr = build_id(
                new_var_name, var2typ[old_var_name], old_var_name)
            add_instr_to_basic_block_front(new_id_instr, instrs)

    return block_vars, n_inserts, updated_block_vars


def var_will_be_overwritten(instrs, idx, var):
    """
    True iff var will be overwritten after index idx in instrs
    """
    for instr in instrs[idx + 1:]:
        if DEST in instr and instr[DEST] == var:
            return True
    return False


def get_from_table(table, num):
    var = list(table.items())[num][1]
    return var


def get_value_from_table(table, num):
    return list(table.keys())[num]


def lvn_value_equality(lvn_val1, lvn_val2, table):
    """
    True if 2 LVN Values are Semantically equivalent
    """
    if lvn_val1 == lvn_val2:
        return True

    # Do Algebraic Simplication
    op1 = lvn_val1[0]
    op2 = lvn_val2[0]

    # A + A = 2 * A
    if op1 == ADD and op2 == MUL:
        if lvn_val1[1] == lvn_val1[2] and lvn_val2[1] == lvn_val1[1] and get_from_table(table, lvn_val2[2]) == (CONST, 2):
            return True
        elif lvn_val1[1] == lvn_val1[2] and lvn_val2[2] == lvn_val1[1] and get_from_table(table, lvn_val2[1]) == (CONST, 2):
            return True
    elif op1 == MUL and op2 == ADD:
        if lvn_val2[1] == lvn_val2[2] and lvn_val1[1] == lvn_val2[1] and get_from_table(table, lvn_val1[2]) == (CONST, 2):
            return True
        elif lvn_val2[1] == lvn_val2[2] and lvn_val1[2] == lvn_val2[1] and get_from_table(table, lvn_val1[1]) == (CONST, 2):
            return True

    # gt == le
    elif op1 == GT and op2 == LE:
        if lvn_val1[1] == lvn_val1[2] and lvn_val2[2] == lvn_val1[1]:
            return True
    elif op1 == LE and op2 == GT:
        if lvn_val1[1] == lvn_val1[2] and lvn_val2[2] == lvn_val1[1]:
            return True
    # lt == ge
    elif op1 == LT and op2 == GE:
        if lvn_val1[1] == lvn_val1[2] and lvn_val2[2] == lvn_val1[1]:
            return True
    elif op1 == GE and op2 == LT:
        if lvn_val1[1] == lvn_val1[2] and lvn_val2[2] == lvn_val1[1]:
            return True

    # add on more identities here...
    return False


def value_in_table(value, table):
    """
    True, value in table if Value is in the Table, else False, None
    """
    assert type(value) == tuple

    for table_value, pair in table.items():
        if lvn_value_equality(value, table_value, table):
            return True, pair

    return False, (None, None)


def lvn_basic_block(basic_block, var2typ):
    """
    Perform LVN on a basic block
    """

    # reset counters
    reset_lvn_num()

    # set up preliminary data structures for lvn pass on basic block
    var2num = dict()
    table = OrderedDict()

    instrs = basic_block[INSTRS]
    block_vars, n_inserts, updated_block_vars = handle_block_vars(
        instrs, var2typ)

    # add in block vars into data structures
    for block_var in block_vars:
        block_num = gen_fresh_lvn_num()
        block_value = (f"{BLOCK_VAR}_{block_num}",)
        var2num[block_var] = block_num
        table[block_value] = block_num, block_var

    new_instrs = []
    # skip over an inserted block var instructions
    for idx, instr in enumerate(instrs[n_inserts:], n_inserts):
        if DEST in instr:
            dst = instr[DEST]
            old_dst = deepcopy(dst)
            value, value_has_changed = instr_to_lvn_value(
                instr, var2num, table)

            value_is_in_table, pair = value_in_table(value, table)
            if value_is_in_table:
                num, var = pair
                new_id_instr = build_id(dst, var2typ[dst], var)
                new_instrs.append(new_id_instr)
            else:
                num = gen_fresh_lvn_num()
                new_instr = deepcopy(instr)

                if var_will_be_overwritten(instrs, idx, dst):
                    dst = gen_fresh_variable(dst)
                else:
                    dst = instr[DEST]
                new_instr[DEST] = dst

                table[value] = num, dst

                # if value did not change, keep changing the new instr
                if not value_has_changed:
                    if ARGS in instr:
                        new_args = []
                        for arg in instr[ARGS]:
                            value, (_, new_arg) = list(
                                table.items())[var2num[arg]]
                            if lvn_value_is_id(value) and get_from_table(table, value[1])[1] not in updated_block_vars:
                                new_arg = get_from_table(table, value[1])[1]
                            new_args.append(new_arg)
                        new_instr[ARGS] = new_args
                # otherwise generate a new instruction completely
                else:
                    new_instr = lvn_value_to_instr(dst, value, table, instr)

                new_instrs.append(new_instr)

            # MAP WITH OLD VARIABLE DESTINATION
            dst = old_dst
            var2num[dst] = num

        # does not have a dest: replace args as appropriate
        else:
            if ARGS in instr:
                new_args = []
                for arg in instr[ARGS]:
                    value, (_, new_arg) = list(
                        table.items())[var2num[arg]]
                    if lvn_value_is_id(value) and get_from_table(table, value[1])[1] not in updated_block_vars:
                        new_arg = get_from_table(table, value[1])[1]
                    new_args.append(new_arg)
                instr[ARGS] = new_args

            new_instrs.append(instr)

    return new_instrs


def lvn_func(func):
    cfg = form_cfg_w_blocks(func)
    var2typ = get_var_types(func)
    for block in cfg:
        new_instrs = lvn_basic_block(cfg[block], var2typ)
        cfg[block][INSTRS] = new_instrs
    final_instrs = join_cfg(cfg)
    return final_instrs


def lvn(program):
    for func in program[FUNCTIONS]:
        new_instrs = lvn_func(func)
        func[INSTRS] = new_instrs
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
