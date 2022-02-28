from copy import deepcopy
import click
import sys
import json

from cfg import form_cfg_succs_preds, join_blocks_w_labels
from dominator_utilities import get_natural_loops
from bril_core_constants import *


LOOP_INVARIANT = True
NOT_LOOP_INVARIANT = not LOOP_INVARIANT


LOOP_PREHEADER_COUNTER = 0
NEW_LOOP_PREHEADER = "new.loop.preheader"


def gen_loop_preheader():
    global LOOP_PREHEADER_COUNTER
    LOOP_PREHEADER_COUNTER += 1
    return f"{NEW_LOOP_PREHEADER}.{LOOP_PREHEADER_COUNTER}"


def insert_preheaders(func):
    instrs = func["instrs"]
    cfg = form_cfg_succs_preds(instrs)
    natural_loops = get_natural_loops(instrs)
    for loop, header in natural_loops:
        preheader =


def identify_loop_invariant_instrs(loop_instrs):
    continue_while = True
    while continue_while:
        for instr in loop_instrs:
            if ARGS in instr:
                args = instr[ARGS]
                for x in args:
                    pass


def move_loop_invariant_instrs():
    pass


def func_licm(func):
    instrs = func["instrs"]


def licm(program):
    """
    LICM wrapper function
    """
    for func in program["functions"]:
        pass


@click.command()
@click.option('--licm', default=False, help='Run Loop Invariant Code Motion.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(licm, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = licm(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
