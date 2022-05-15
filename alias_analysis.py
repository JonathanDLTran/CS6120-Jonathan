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

from numpy import block

from worklist_solver import Worklist

from cfg import form_cfg, form_block_dict, form_blocks

from bril_core_constants import *
from bril_core_utilities import *

from bril_memory_extension_constants import *
from bril_memory_extension_utilities import *


def gen_heap_loc(basic_block, idx):
    return f"{basic_block}_at_{idx}"


def regularize_type(typ):
    if type(typ) == dict:
        assert PTR in typ 
        return (PTR, regularize_type(typ[PTR]))
    return typ


def deregularize_type(typ):
    if type(typ) == tuple and len(typ) == 1:
        return typ[0]
    if type(typ) == tuple:
        assert typ[0] == PTR
        return f"ptr<{deregularize_type(typ[1:])}>"
    return typ

def merge(variables_lst):
    if len(variables_lst) < 1:
        raise RuntimeError("Expects 1 or more list of variables")
    final_variables = variables_lst[0]
    for lst in variables_lst:
        for v in lst:
            final_variables[v] = final_variables[v].union(lst[v])
    return final_variables


def transfer_helper(variables, block, index):
    new_variables = deepcopy(variables)
    for i, instr in enumerate(block):
        if i > index:
            break
        if is_ptr_type(instr):
            typ = regularize_type(instr[TYPE])
            if is_ptradd(instr):
                # union to move up lattice
                ptr_arg = instr[ARGS][0]
                new_variables[(instr[DEST], typ)] = new_variables[(instr[DEST], typ)].union(new_variables[(ptr_arg, typ)])
            elif is_id(instr):
                # to move up the lattice, we have to union
                ptr_arg = instr[ARGS][0]
                new_variables[(instr[DEST], typ)] = new_variables[(instr[DEST], typ)].union(new_variables[(ptr_arg, typ)])
            elif is_alloc(instr):
                # note that union will not duplicate heap locs
                # only 1 heap loc created at each syntactic location
                new_variables[(instr[DEST], typ)] = new_variables[(instr[DEST], typ)].union({gen_heap_loc(str(id(block)), i)})
            elif is_load(instr):
                # because we don't use any context in this analysis, a load will
                # allov a variable to point to ANY locations of any variable of the same type
                # because some one may have wrote to those locations and are
                # reading from them now
                locations = set()
                for var_name, unregularized_var_typ in new_variables:
                    var_typ = regularize_type(unregularized_var_typ)
                    if var_typ == typ:
                        locations = locations.union(new_variables[var_name, var_typ])
                new_variables[(instr[DEST], typ)] = new_variables[(instr[DEST], typ)].union(locations)
    return new_variables


def transfer(variables, block):
    """
    Transfer function

    Assumes Worklist Solver does not copy or mutate blocks
    as this routine uses the id(block)!
    """
    return transfer_helper(variables, block, len(block))


def init_all_vars(func):
    """
    Set up map of all memory variables in a function to an empty set
    Used at the beginning of forward data flow analysis

    Key to the map is the variable name and type
    """
    variables = OrderedDict()
    for instr in func[INSTRS]:
        if is_ptr_type(instr) and DEST in instr:
            typ = regularize_type(instr[TYPE])
            variables[(instr[DEST], typ)] = set()
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
                a_type = regularize_type(a[TYPE])
                init[(a[NAME], a_type)] = set()
    worklist = Worklist(entry, cfg, blocks, init, merge, transfer)
    return worklist.solve()


def alias_analysis(prog):
    output = OrderedDict()
    for func in prog[FUNCTIONS]:
        (in_dict, out_dict) = func_alias_analysis(func)
        output[func[NAME]] = (in_dict, out_dict)
    return output


def intra_block_alias_analysis(global_aa, func, cfg, block_name, index):
    """
    Perform Alias Analysis in an INTRA block setting
    Goes up until index, and includes index's execution

    Index must be a valid index corresponding to an instruction in block_name
    """
    variables_map = global_aa[func][0][block_name]
    block_instrs = cfg[block_name][INSTRS]
    return transfer_helper(variables_map, block_instrs, index)


def pretty_print_alias_analysis(prog):
    for func in prog[FUNCTIONS]:
        (in_dict, out_dict) = func_alias_analysis(func)

        final_in_dict = OrderedDict()
        for (bb, inner_dict) in in_dict.items():
            inner_lst = list(
                sorted([kv for kv in inner_dict.items()], key=lambda kv: kv[0][0]))
            final_in_dict[bb] = inner_lst
        final_out_dict = OrderedDict()
        for (bb, inner_dict) in out_dict.items():
            inner_lst = list(
                sorted([kv for kv in inner_dict.items()], key=lambda kv: kv[0][0]))
            final_out_dict[bb] = inner_lst

        print(f"Function: {func[NAME]}")
        print(f"In:")
        for (k, v) in final_in_dict.items():
            if v == []:
                print(f"\tBB {k}: No Aliasing at the start of Basic Block {k}.")
            else:
                for ((var, var_typ), locs) in v:
                    print(f"\tBB {k}, Var {var}, Typ {deregularize_type(var_typ)}: {{{', '.join(locs)}}}.")
        print(f"Out:")
        for (k, v) in final_out_dict.items():
            if v == []:
                print(f"\t{k}: No Aliasing at the end of Basic Block {k}.")
            else:
                for ((var, var_typ), locs) in v:
                    print(f"\tBB {k}, Var {var}, Typ {deregularize_type(var_typ)}: {{{', '.join(locs)}}}.")
    return


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    pretty_print_alias_analysis(prog)


if __name__ == "__main__":
    main()
