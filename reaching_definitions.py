import sys
import json
import click

from cfg import form_cfg
from bril_core_constants import *


def kills(block):
    assert type(block) == list
    kills = set()
    for instr in block:
        if DEST in instr:
            dst = instr[DEST]
            kills.add(dst)
    return kills


def defs(block):
    assert type(block) == list
    variables = dict()
    for (idx, instr) in block:
        if DEST in instr:
            dst = instr[DEST]
            # get most recent variable assignment to dst in basic block
            variables[dst] = idx

    defs = set()
    for dst, idx in variables.items():
        defs.add((idx, dst))
    return defs


def diff(in_block, kills):
    assert type(in_block) == set
    assert type(kills) == set
    final = set()
    for (i1, var1) in in_block:
        killed = False
        for (_, var2) in kills:
            if var1 == var2:
                killed = True
                break
        if not killed:
            final.add(i1, var1)
    return final


def transfer_function(in_block, block):
    assert type(in_block) == set
    assert type(block) == list
    return defs(block).union(diff(in_block, kills(block)))


def merge(blocks):
    merged = set()
    for b in blocks:
        merged = merged.union(b)
    return merged


def number_instrs(cfg):
    """
    Adds unique instruction labels to every instruction with a destination
    """
    i = 1
    for name, block in cfg:
        new_block = []
        for instr in block:
            new_block.append((i, instr))
            i += 1
        cfg[name] = new_block
    return cfg


def reaching_defs(program):
    cfg = form_cfg(program)
    numbered_cfg = number_instrs(cfg)


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
