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
"""


import click
from copy import deepcopy
import sys
import json

from collections import OrderedDict


from bril_speculation_utilities import is_guard


from cfg import form_blocks, join_blocks
from bril_core_constants import *


LVN_NUMBER = 0
VARIABLE_NUMBER = 0


ARG_LVN_VALUE = "arg-value"
PREV_DEFINED_VAR = "prev-defined-var"


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


def gen_fresh_lvn_num():
    global LVN_NUMBER
    LVN_NUMBER += 1
    return LVN_NUMBER


def gen_fresh_variable(var):
    global VARIABLE_NUMBER
    VARIABLE_NUMBER += 1
    return f"{var}_{VARIABLE_NUMBER}_lvn"


def instr_to_lvn_value(instr, var2num):
    assert type(instr) == dict
    return Lvn_value(instr, var2num)


def lvn_func(func):

    # set up preliminary data structures for lvn pass
    var2num = dict()
    table = OrderedDict()

    for instr in func[INSTRS]:
        if DEST in instr and ARGS in instr:
            num = instr_to_lvn_value(instr, var2num)
            print(num)
        # special case values
        elif DEST in instr and ARGS not in instr:
            pass
        # all other cases
        else:
            pass


def lvn(program):
    for func in program[FUNCTIONS]:
        lvn_func(func)


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
