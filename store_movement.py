"""
Move Stores to be later in the basic block, to increase the size
of vectorization
"""

import click
import sys
import json

from bril_core_constants import *
from bril_core_utilities import *
from bril_memory_extension_utilities import is_load, is_mem, is_store

from alias_analysis import func_alias_analysis, may_alias
from cfg import form_cfg_w_blocks, join_cfg


def move_stores_basic_block(basic_block_instrs, end_basic_block_alias_analysis):
    # begin by storing new instruction order in reverse order
    # instructions closer to the front are in later in the basic block
    new_basic_block_instrs = []
    for instr in reversed(basic_block_instrs):
        # the following code is almost verbatim translated to python3 from c++ code I wrote for Disopyros
        if not is_store(instr):
            new_basic_block_instrs.append(instr)
            continue
        # consider only moving store instructions back
        move_before_store_list = []
        while True:
            if new_basic_block_instrs == []:
                new_basic_block_instrs.append(instr)
                break
            last_instr = new_basic_block_instrs[-1]
            if is_mem(last_instr):
                store_ptr = instr[ARGS][0]
                if is_load(last_instr):
                    other_store_ptr = last_instr[ARGS][0]
                    if may_alias(end_basic_block_alias_analysis, store_ptr, other_store_ptr):
                        new_basic_block_instrs.append(instr)
                        break
                elif is_store(last_instr):
                    load_ptr = last_instr[ARGS][0]
                    if may_alias(end_basic_block_alias_analysis, store_ptr, load_ptr):
                        new_basic_block_instrs.append(instr)
                        break
                else:
                    # for frees/allocs/ptradds, to avoid complications, just don't allow stores to move past them.
                    new_basic_block_instrs.append(instr)
                    break
            last_instr = new_basic_block_instrs.pop()
            move_before_store_list.append(last_instr)
        new_basic_block_instrs += move_before_store_list

    # finish by changing to un-reversed order
    new_basic_block_instrs = list(reversed(new_basic_block_instrs))
    return new_basic_block_instrs


def move_stores_function(func):
    cfg = form_cfg_w_blocks(func)
    _, aa = func_alias_analysis(func)
    for basic_block in cfg:
        new_basic_block_instrs = move_stores_basic_block(
            cfg[basic_block][INSTRS], aa[basic_block])
        cfg[basic_block][INSTRS] = new_basic_block_instrs

    new_instrs = join_cfg(cfg)
    func[INSTRS] = new_instrs
    return func


def move_stores_prog(prog):
    for func in prog[FUNCTIONS]:
        move_stores_function(func)
    return prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Moving Stores.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = move_stores_prog(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
