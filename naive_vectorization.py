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
from bril_core_utilities import build_add, build_const
from bril_memory_extension_utilities import is_store
from bril_vector_constants import *
from bril_vector_utilities import *

from cfg import form_cfg_w_blocks, join_cfg

from vectorization_utilities import *


def instr_run_to_vector(instrs):
    assert len(instrs) > 0
    assert is_homogenous(instrs)
    assert is_independent(instrs)

    first_instr = instrs[0]
    op_type = first_instr[OP]
    assert op_type not in VEC_OPS
    vec_op_type = OP_TO_VECOP[op_type]
    assert vec_op_type in VEC_BINOPS

    left_args = []
    right_args = []
    prior_dests = []
    for instr in instrs:
        assert ARGS in instr
        args = instr[ARGS]
        assert len(args) == 2
        left_args.append(args[0])
        right_args.append(args[1])
        assert DEST in instr
        prior_dests.append(instr[DEST])

    # set up needed expressons for vectorization
    left_vec_name = gen_new_vector_var()
    empty_left_vec_instr = build_veczero(left_vec_name)

    right_vec_name = gen_new_vector_var()
    empty_right_vec_instr = build_veczero(right_vec_name)

    one_name = gen_new_vector_one()
    one_instr = build_const(one_name, INT, 1)

    index_name = gen_new_vector_idx()
    index_instr = build_const(index_name, INT, 0)

    vector_instrs = [one_instr,
                     index_instr,
                     empty_left_vec_instr,
                     empty_right_vec_instr]

    # load into vector
    for i in range(len(instrs)):
        left_vecload_instr = build_vecload(
            left_vec_name, index_name, left_args[i])
        right_vecload_instr = build_vecload(
            right_vec_name, index_name, right_args[i])
        # no need to incr index on last iteration
        if i != len(instrs) - 1:
            incr_index_instr = build_add(index_name, index_name, one_name)
            vector_instrs += [left_vecload_instr,
                              right_vecload_instr, incr_index_instr]
        else:
            vector_instrs += [left_vecload_instr,
                              right_vecload_instr]

    # do the operation
    vecop_result_name = gen_result_vector_var()
    vecop_instr = build_vecbinop(
        vecop_result_name, left_vec_name, right_vec_name, vec_op_type)
    vector_instrs.append(vecop_instr)

    # extract elements from the vector
    reset_index_instr = build_const(index_name, INT, 0)
    vector_instrs.append(reset_index_instr)

    for i in range(len(instrs)):
        extract_instr = build_vecstore(
            prior_dests[i], vecop_result_name, index_name)
        incr_index_instr = build_add(index_name, index_name, one_name)
        # no need to incr index on last iteration
        if i != len(instrs) - 1:
            vector_instrs += [extract_instr,
                              incr_index_instr]
        else:
            vector_instrs += [extract_instr]

    return vector_instrs


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
    # insert these vector instructions right after the last instruction in the run
    for run_instrs in runs:
        assert len(run_instrs) > 0
        vectorized_instrs = instr_run_to_vector(run_instrs)
        # find the right location
        final_run_instr = run_instrs[-1]
        final_idx = 0
        for i, instr in enumerate(basic_block_instrs):
            if id(instr) == id(final_run_instr):
                final_idx = i + 1  # do 1 more to insert after
        basic_block_instrs = basic_block_instrs[:final_idx] + \
            vectorized_instrs + basic_block_instrs[final_idx:]

    # Delete old instructions. We don't have to worry about instructions that are
    # used outside the run (e.g. in some other block, later in the block, or
    # earlier in the block (for phi nodes) because we extract every element from the
    # naive vector generated. Further, we don't transform any operations, so every
    # original opcode is represented by exactly one vector lane and vice versa

    final_basic_block_instrs = []

    run_instrs_set = set()
    for run_instrs in runs:
        for instr in run_instrs:
            run_instrs_set.add(id(instr))

    for instr in basic_block_instrs:
        if id(instr) not in run_instrs_set:
            final_basic_block_instrs.append(instr)

    return final_basic_block_instrs


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
