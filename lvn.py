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
    return f"{var}_{VARIABLE_NUMBER}_lvn"


def lvn(program):
    pass


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
