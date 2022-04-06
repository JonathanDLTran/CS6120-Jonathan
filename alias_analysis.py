import json
import sys
import click
from collections import OrderedDict
from copy import deepcopy

from worklist_solver import Worklist

from cfg import form_cfg_w_blocks

from bril_core_constants import *
from bril_core_utilities import *

from bril_memory_extension_constants import *
from bril_memory_extension_utilities import *


HEAP_LOC_IDX = 0


def gen_heap_loc():
    global HEAP_LOC_IDX
    HEAP_LOC_IDX += 1
    return HEAP_LOC_IDX


def merge(variables_lst):
    if len(variables_lst) < 1:
        raise RuntimeError("Expects 1 or more list of variables")
    final_variables = variables_lst[0]
    for lst in variables_lst:
        for v in lst:
            final_variables[v] = final_variables[v].union(lst[v])
    return final_variables


def transfer(variables, block):
    new_variables = deepcopy(variables)
    for instr in block[INSTRS]:
        if is_const(instr):
            new_variables[instr[DEST]] = set()
        elif is_id(instr):
            new_variables[instr[DEST]] = variables[instr[ARGS][0]]
        elif is_alloc(instr):
            new_variables[instr[DEST]] = gen_heap_loc()
    return new_variables


def init_all_vars(func):
    variables = OrderedDict()
    for instr in func[INSTRS]:
        if DEST in instr:
            variables[instr[DEST]] = set()
    return variables


def func_alias_analysis(func):
    cfg = form_cfg_w_blocks(func)
    variables = init_all_vars(func)


def alias_analysis():
    pass


def main():
    pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
@click.option('--aa', default=False, help='Perform Alias Analysis.')
def main(fusion, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    pass


if __name__ == "__main__":
    main()
