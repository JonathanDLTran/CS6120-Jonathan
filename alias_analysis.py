"""
Basic Alias Analysis

TODO: Figuring out how alias analysis works and debugging
TODO: rewrite the transfer functions
"""

import json
import sys
import click
from collections import OrderedDict
from copy import deepcopy

from worklist_solver import Worklist

from cfg import form_cfg, form_block_dict, form_blocks

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
    for instr in block:
        if is_ptr_type(instr):
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
        if is_mem(instr) and DEST in instr:
            variables[instr[DEST]] = set()
    return variables


def func_alias_analysis(func):
    cfg = form_cfg(func)
    assert len(cfg) != 0
    entry = list(cfg.items())[0][0]
    blocks = form_block_dict(form_blocks(func["instrs"]))
    init = init_all_vars(func)
    if ARGS in func:
        args = func[ARGS]
        for a in args:
            if is_ptr_type(a):
                init[a[NAME]] = set()
    worklist = Worklist(entry, cfg, blocks, init, merge, transfer)
    return worklist.solve()


def alias_analysis(prog):
    for func in prog[FUNCTIONS]:
        (in_dict, out_dict) = func_alias_analysis(func)

        final_in_dict = OrderedDict()
        for (key, inner_set) in in_dict.items():
            inner_lst = list(
                sorted([pair for pair in inner_set], key=lambda pair: pair[0]))
            final_in_dict[key] = inner_lst
        final_out_dict = OrderedDict()
        for (key, inner_set) in out_dict.items():
            inner_lst = list(
                sorted([pair for pair in inner_set], key=lambda pair: pair[0]))
            final_out_dict[key] = inner_lst

        print(f"Function: {func[NAME]}")
        print(f"In:")
        for (k, v) in final_in_dict.items():
            if v == []:
                print(f"\t{k}: No Aliasing at the start of Basic Block {k}.")
            else:
                print(f"\t{k}: {{{', '.join(v)}}}.")
        print(f"Out:")
        for (k, v) in final_out_dict.items():
            if v == []:
                print(f"\t{k}: No Aliasing at the end of Basic Block {k}.")
            else:
                print(f"\t{k}: {{{', '.join(v)}}}.")
    return


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    alias_analysis(prog)


if __name__ == "__main__":
    main()
