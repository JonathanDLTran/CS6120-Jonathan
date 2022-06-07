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
from bril_core_utilities import build_id


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


def instr_to_lvn_value(instr):
    assert type(instr) == dict
    assert OP in instr

    args = []
    if ARGS in instr:
        args = instr[ARGS]
    else:
        args = [instr[VALUE]]

    return (instr[OP], *args)


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
    for old_var_name in block_vars:

        has_old_var_def = False
        for instr in instrs:
            if DEST in instr and instr[DEST] == old_var_name:
                has_old_var_def = True

        if has_old_var_def:
            n_inserts += 1

            new_var_name = gen_fresh_variable(old_var_name)
            rename_vars(old_var_name, new_var_name, instrs)
            assert old_var_name in var2typ
            new_id_instr = build_id(
                new_var_name, var2typ[old_var_name], old_var_name)
            add_instr_to_basic_block_front(new_id_instr, instrs)

    return block_vars, n_inserts


def var_will_be_overwritten(instrs, idx, var):
    """
    True iff var will be overwritten after index idx in instrs
    """
    # print(var)
    # print(idx)
    # print(instrs)
    for instr in instrs[idx + 1:]:
        if DEST in instr and instr[DEST] == var:
            return True
    return False


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
    block_vars, n_inserts = handle_block_vars(instrs, var2typ)

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
            value = instr_to_lvn_value(instr)

            if value in table:
                num, var = table[value]
                new_id_instr = build_id(dst, var2typ[dst], var)
                new_instrs.append(new_id_instr)
            else:
                num = gen_fresh_lvn_num()

                if var_will_be_overwritten(instrs, idx, dst):
                    dst = gen_fresh_variable(dst)
                    instr[DEST] = dst
                else:
                    dst = instr[DEST]

                table[value] = num, dst

                if ARGS in instr:
                    new_args = []
                    for arg in instr[ARGS]:
                        # print(table)
                        # print(var2num)
                        # print(arg)
                        new_args.append(list(table.values())[var2num[arg]][1])
                    instr[ARGS] = new_args

                new_instrs.append(instr)

            # MAP WITH OLD VARIABLE DESTINATION
            dst = old_dst
            var2num[dst] = num

        # does not have a dest: replace args as appropriate
        else:
            if ARGS in instr:
                new_args = []
                for arg in instr[ARGS]:
                    new_args.append(list(table.values())[var2num[arg]][1])
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
