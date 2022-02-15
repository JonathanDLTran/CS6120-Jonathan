"""
Live Variables Analysis

We use the following transfer function, t(.)
such that in(b) = t(out(b), b)

Note that a def automatically kills a live variable
But a use will make another variable live.

in(b) = out(b) - defs(b)

The merge function is defined as:
merge(blocks) = union
The reason is that variables used later, on different branches,
such all be considered together.
E.g. if branch1 uses a later, and branch2 uses a and b later,
then not considering the branches, both a and b are used later.

Problem: We need instructions to be both used later on, and also
having been defined prior to use.
"""


import sys
import json
import click
from collections import OrderedDict

from cfg import form_cfg, form_blocks, form_block_dict
from bril_core_constants import *
from worklist_solver import Worklist


def defs(block):
    """ Equivalent to Kills """
    assert type(block) == list
    defs = set()
    for instr in block:
        if DEST in instr:
            dst = instr[DEST]
            defs.add(dst)
    return defs


def uses(block):
    """ Equivalent to Gens

    Grab uses after defs, but defs remove all uses of same variable

    We iterate backwards to preserve the ordering of Live Variables Analysis
    """
    assert type(block) == list
    uses = set()
    for instr in reversed(block):
        # Do Defs first
        if DEST in instr:
            dst = instr[DEST]
            if dst in uses:
                uses.remove(dst)
        # Do Uses second
        if ARGS in instr:
            args = instr[ARGS]
            for a in args:
                uses.add(a)
    return uses


def diff(in_block, kills):
    assert type(in_block) == set
    assert type(kills) == set
    final = set()
    for var in in_block:
        killed = False
        for kill_var in kills:
            if var == kill_var:
                killed = True
        if not killed:
            final.add(var)
    return final


def transfer(in_block, block):
    assert type(in_block) == set
    assert type(block) == list
    return uses(block).union(diff(in_block, defs(block)))


def merge(blocks):
    result = set()
    for b in blocks:
        result = result.union(b)
    return result


def live_variables_func(function):
    cfg = form_cfg(function)
    assert len(cfg) != 0
    entry = list(cfg.items())[0][0]
    blocks = form_block_dict(form_blocks(function["instrs"]))
    init = set()
    worklist = Worklist(entry, cfg, blocks, init, merge, transfer)
    return worklist.solve_backwards()


def live_variables(program):
    for func in program["functions"]:
        (in_dict, out_dict) = live_variables_func(func)

        # sort the dictionaries into lists, where we alphabetically order variables
        final_in_dict = OrderedDict()
        for (key, inner_set) in in_dict.items():
            inner_lst = list(
                sorted([v for v in inner_set]))
            final_in_dict[key] = inner_lst
        final_out_dict = OrderedDict()
        for (key, inner_set) in out_dict.items():
            inner_lst = list(
                sorted([v for v in inner_set]))
            final_out_dict[key] = inner_lst

        print(f"Function: {func[NAME]}")
        print(f"In:")
        for (k, v) in final_in_dict.items():
            if v == []:
                print(f"\t{k}: No Live Variables.")
            else:
                for var in v:
                    print(f"\t{k}: {var} used.")
        print(f"Out:")
        for (k, v) in final_out_dict.items():
            if v == []:
                print(f"\t{k}: No Live Variables.")
            else:
                for var in v:
                    print(f"\t{k}: {var} used.")
    return


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    live_variables(prog)


if __name__ == "__main__":
    main()
