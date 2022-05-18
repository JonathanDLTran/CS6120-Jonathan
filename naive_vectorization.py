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
from bril_memory_extension_utilities import is_store
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


def instr_used(vector_run, instr):
    """
    True if instr uses as any of its arguments any variable defined for an instruction in vector run
    """
    if ARGS not in instr:
        return False
    for past_instr in vector_run:
        assert DEST in past_instr
        if past_instr[DEST] in instr[ARGS]:
            return True
    return False


def naive_vectorization_basic_block(basic_block_instrs, func):
    """
    Iterate over instructions in basic block

    When you hit an instruction that is vectorizable:
    - add it to a list of instructions to vectorize

    - Terminate this list when you see a
    --- The beginning another type of vectorizable instruction
    --- use of any vectoriable instruction
        -- An update of any variable in the lit
    -- ANY STORE: because this could overwrite data needed for an early vectorized load 
    -- vector run hits vector lane width
    -- end of basic block 
    """
    runs = []
    vector_run = []
    for instr in basic_block_instrs:
        # not yet begun vectorizing a run
        if vector_run == []:
            if instr_is_vectorizable(instr):
                vector_run.append(instr)
        # vectorizing a run
        else:
            last_instr = vector_run[-1]
            last_instr_op = last_instr[OP]
            if instr_is_vectorizable(instr) and last_instr_op != instr[OP]:
                runs.append(vector_run)
                vector_run = []
            elif instr_used(vector_run, instr):
                runs.append(vector_run)
                vector_run = []
            elif is_store(instr):
                runs.append(vector_run)
                vector_run = []
            elif len(vector_run) == VECTOR_LANE_WIDTH:
                runs.append(vector_run)
                vector_run = []

            # otherwise check if still vectorizable and add
            if instr_is_vectorizable(instr):
                vector_run.append(instr)

    if vector_run != []:
        runs.append(vector_run)

    # Now Change Each Run to use Vector Instructions and Stitch Back into Basic Block


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
