from copy import deepcopy
from collections import OrderedDict
import click
import sys
import json

from cfg import form_cfg_w_blocks, insert_into_cfg, join_cfg
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


def insert_preheaders(natural_loops, cfg):
    headers = set()
    preheadermap = OrderedDict()
    backedgemap = OrderedDict()
    for _, (A, _), header in natural_loops:
        if header not in backedgemap:
            backedgemap[header] = [A]
        else:
            backedgemap[header].append(A)
    for _, _, header in natural_loops:
        if header in headers:
            # loop header shared with another prior loop header
            continue
        preheader = gen_loop_preheader()
        headers.add(header)
        preheadermap[header] = preheader
        insert_into_cfg(preheader, backedgemap[header], header, cfg)
    return preheadermap


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
    natural_loops = get_natural_loops(func)
    cfg = form_cfg_w_blocks(func)
    preheadermap = insert_preheaders(natural_loops, cfg)
    return join_cfg(cfg)


def licm_main(program):
    """
    LICM wrapper function
    """
    for func in program["functions"]:
        modified_func_instrs = func_licm(func)
        func["instrs"] = modified_func_instrs
    return program


@click.command()
@click.option('--licm', default=False, help='Run Loop Invariant Code Motion.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(licm, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if licm:
        final_prog = licm_main(prog)
    else:
        final_prog = prog
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
