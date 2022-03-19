"""
Implementation of Induction Variable Elimination for Loops 
"""

import sys
import json
import click

from licm import insert_preheaders
from cfg import form_cfg_w_blocks, join_cfg, INSTRS
from dominator_utilities import get_natural_loops
from bril_core_constants import *


class InductionVariable(object):
    def __init__(self, identifier, c, d, basic, varname) -> None:
        self.identifier = identifier
        self.c = c
        self.d = d
        self.basic = basic
        self.varname = varname


def find_loop_invariant(loop):
    """
    An instruction is loop invariant  
    """
    pass


def find_basic_ivs():
    pass


def find_derived_ivs():
    pass


def replace_ivs():
    pass


def func_induction_variables(func):
    natural_loops = get_natural_loops(func)
    old_cfg = form_cfg_w_blocks(func)
    instrs_w_blocks = []
    for block in old_cfg:
        for instr in old_cfg[block][INSTRS]:
            instrs_w_blocks.append((instr, block))
    preheadermap, new_instrs = insert_preheaders(
        natural_loops, instrs_w_blocks)
    func[INSTRS] = new_instrs
    cfg = form_cfg_w_blocks(func)

    for natural_loop in natural_loops:
        pass


def induction_variables(prog):
    for func in prog[FUNCTIONS]:
        new_instrs = func_induction_variables(func)
        func[INSTRS] = new_instrs
    return prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
@click.option('--ive', default=False, help='Run Induction Variable Elimination Original Program.')
def main(pretty_print, ive):
    prog = json.load(sys.stdin)
    if pretty_print == 'True':
        print(json.dumps(prog, indent=4, sort_keys=True))
    if ive == 'True':
        final_prog = induction_variables(prog)
    else:
        final_prog = prog
    if pretty_print == 'True':
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
