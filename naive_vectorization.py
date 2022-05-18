"""
Exceptionally Naive Vectorization

- Looks for runs of code with isomorphic, independent operations, and loads
them into a vector, then extracts from the vector

Search for groups of instructions that can be obviously vectorized and generate
them as vector instructions, in a greedy fashion

Iterate over instructions. When a run of instructions that are isomorphic are detected,
group them together 
Then translate those instructions to vector instructions, inserting loads and extracts
as required.
"""

import click
import sys
import json

from bril_core_constants import *
from bril_core_utilities import is_add, is_div, is_mul, is_sub
from bril_vector_constants import *
from bril_vector_utilities import *

from cfg import form_cfg_w_blocks, join_cfg


def is_homogenous(instrs):
    assert len(instrs) > 0
    assert OP in instrs[0]
    first_op = instrs[0][OP]
    for instr in instrs:
        if instr[OP] != first_op:
            return False
    return True


def is_independent(instrs):
    # TODO
    return False


def instr_run_to_vector(instrs):
    assert len(instrs) == VECTOR_LANE_WIDTH
    assert is_homogenous(instrs)
    assert is_independent(instrs)


def instr_is_vectorizable(instr):
    return is_add(instr) or is_sub(instr) or is_mul(instr) or is_div(instr)


def naive_vectorization_basic_block(basic_block_instrs, func):
    for instr in basic_block_instrs:
        print(instr)


def naive_vectorization_func(func):
    cfg = form_cfg_w_blocks(func)
    for basic_block in cfg:
        new_instrs = naive_vectorization_basic_block(
            cfg[basic_block][INSTRS], func)
        cfg[basic_block][INSTRS] = new_instrs

    final_instrs = join_cfg(cfg)
    func[INSTRS] = final_instrs
    return func


def naive_vectorization_prog(prog):
    for func in prog[FUNCTIONS]:
        naive_vectorization_func(func)
    return prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Naive Vectorization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = naive_vectorization_prog(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
