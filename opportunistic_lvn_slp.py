"""
SLP style vectorization, where I opportunistically vectorize code by creating
vector packs were I can, and see if those packs can be used later on.

In this vectorization style, there is no attempt to backtrack or try various other packing heuristic .
"""

import click
import json
import sys

from bril_core_constants import *
from bril_core_utilities import *
from bril_vector_utilities import build_vecbinop, build_vecload, build_vecmove, build_vecstore, build_veczero

from cfg import form_cfg_w_blocks, join_cfg

from ssa import bril_to_ssa, ssa_to_bril

from vectorization_utilities import *


MAX_RUNS_HANDLED = 4

MIN_MATCHES_FOR_PARTIAL = 2


def run_to_triples(run):
    """
    Convert a run to a list of triples, where each triple is (dest, arg1, arg2)
    """
    assert type(run) == list
    assert len(run) > 0

    triples = []
    for instr in run:
        assert ARGS in instr
        assert len(instr[ARGS]) == NUM_BINARY_ARGS
        assert DEST in instr

        triple = (instr[DEST], instr[ARGS][0], instr[ARGS][1])
        triples.append(triple)
    return triples


def triples_to_left_args(triples):
    left_args = []
    for triple in triples:
        left_args.append(triple[1])
    return tuple(left_args)


def triples_to_right_args(triples):
    right_args = []
    for triple in triples:
        right_args.append(triple[2])
    return tuple(right_args)


def triples_to_dests(triples):
    dests = []
    for triple in triples:
        dests.append(triple[0])
    return tuple(dests)


def partially_matches_pack(args, previously_computed_pack):
    """
    True and match indices if args matches a computed pack on more than MIN_MATCHES
    """
    arg_len = len(args)
    previously_computed_pack_len = len(previously_computed_pack)
    min_len = min(arg_len, previously_computed_pack_len)
    num_matched = 0
    unmatched_indices = []
    for i in range(min_len):
        if args[i] == previously_computed_pack[i]:
            num_matched += 1
        else:
            unmatched_indices.append(i)
    return (num_matched >= MIN_MATCHES_FOR_PARTIAL, unmatched_indices)


def partially_matches(args, previously_computed_packs):
    for pack in previously_computed_packs:
        (match, match_indices) = partially_matches_pack(args, pack)
        if match:
            return (match, previously_computed_packs[pack], match_indices)
    return (False, "", [])


def build_arg_vector_partial_match(match_params, run_instrs, previously_computed_constants, vec_args):
    (_, vec_name, unmatched_indices) = match_params
    assert len(unmatched_indices) > 1

    # get pack name and copy it to a fresh vector register via a vecmove
    new_vec_name = gen_new_vector_var()
    vecmove_instr = build_vecmove(new_vec_name, vec_name)
    run_instrs.append(vecmove_instr)

    prior_vector_idx_name = gen_new_vector_idx()
    prior_idx = 0
    new_idx_instr = build_const(prior_vector_idx_name, INT, prior_idx)
    run_instrs.append(new_idx_instr)

    # fill in all differing indexes with vecloads
    for idx in unmatched_indices:
        # build a bump index instruction
        if idx != prior_idx:
            assert idx > prior_idx
            diff = idx - prior_idx
            # build the diff offset constant
            diff_name = None
            if diff not in previously_computed_constants:
                diff_name = gen_new_vector_const()
                new_const_instr = build_const(diff_name, INT, diff)
                run_instrs.append(new_const_instr)
                # add the diff constant to the map of prior built constants
                previously_computed_constants[diff] = diff_name
            else:
                diff_name = previously_computed_constants[diff]
            assert diff_name != None

            # update prior_idx
            prior_idx = idx

            # build the bump incr instruction
            ith_new_vector_idx_name = gen_new_vector_idx()
            incr_instr = build_add(
                ith_new_vector_idx_name, prior_vector_idx_name, diff_name)
            run_instrs.append(incr_instr)
            prior_vector_idx_name = ith_new_vector_idx_name

        # build the vector load instruction
        # build the vector load
        vec_load_instr = build_vecload(
            new_vec_name, prior_vector_idx_name, vec_args[idx])
        run_instrs.append(vec_load_instr)

    return new_vec_name


def build_arg_vector(run_instrs, pack_length, previously_computed_constants, vec_args):
    """
    Build up instructions for a single vector corresponding to one-sided arg inputs to binary operations
    """
    vec_name = gen_new_vector_var()
    vec_instr = build_veczero(vec_name)
    new_vector_idx_name = gen_new_vector_idx()
    new_idx_instr = build_const(new_vector_idx_name, INT, 0)
    run_instrs.append(vec_instr)
    run_instrs.append(new_idx_instr)

    prior_vector_idx_name = new_vector_idx_name
    for i in range(pack_length):
        one_name = None
        if 1 not in previously_computed_constants:
            one_name = gen_new_vector_one()
            one_instr = build_const(one_name, INT, 1)
            run_instrs.append(one_instr)
            # add the one constant to the map of prior built constants
            previously_computed_constants[1] = one_name
        else:
            one_name = previously_computed_constants[1]
        assert one_name != None

        # build the vector load
        vec_load_instr = build_vecload(
            vec_name, prior_vector_idx_name, vec_args[i])
        run_instrs.append(vec_load_instr)

        # only increment if not last member of pack
        if i < pack_length - 1:
            ith_new_vector_idx_name = gen_new_vector_idx()
            incr_instr = build_add(
                ith_new_vector_idx_name, prior_vector_idx_name, one_name)
            run_instrs.append(incr_instr)
            prior_vector_idx_name = ith_new_vector_idx_name

    return vec_name


def destruct_result_vector(result_vector_name, dests, previously_computed_constants, run_instrs):
    pack_length = len(dests)

    assert 1 in previously_computed_constants
    one_name = previously_computed_constants[1]

    # initialize vector iteration variable
    prior_vector_idx_name = gen_new_vector_idx()
    new_idx_instr = build_const(prior_vector_idx_name, INT, 0)
    run_instrs.append(new_idx_instr)

    for i in range(pack_length):

        # build the vector store
        vec_store_instr = build_vecstore(
            dests[i], result_vector_name, prior_vector_idx_name)
        run_instrs.append(vec_store_instr)

        # only increment if not last member of pack
        if i < pack_length - 1:
            ith_new_vector_idx_name = gen_new_vector_idx()
            incr_instr = build_add(
                ith_new_vector_idx_name, prior_vector_idx_name, one_name)
            run_instrs.append(incr_instr)
            prior_vector_idx_name = ith_new_vector_idx_name


def walk_and_build_packs(runs, previously_computed_packs, previously_computed_constants, run_idx, run_to_packs):
    """
    Walk over and build packs for each run

    previously_computed_packs is a map from a pack to a unique variable for that pack
    previously_computed_constants is a map from a constant to the unique variable for that constant
        - this map must be immutable once the key-value pair is added
    run_to_packs maps run_idx to the generated vector pack instructions
    run_idx is a unique integer identifier for each run
    """
    # No Runs: Base Case
    if len(runs) == 0:
        return run_to_packs

    # Start Translating first run to vectors
    run = runs[0]
    assert 0 < len(run) <= VECTOR_LANE_WIDTH
    assert is_homogenous(run)
    assert is_independent(run)

    # grab instructoon type
    first_instr = run[0]
    op_type = first_instr[OP]
    assert op_type not in VEC_OPS
    vec_op_type = OP_TO_VECOP[op_type]
    assert vec_op_type in VEC_BINOPS

    # grab data from each run
    triples = run_to_triples(run)
    left_args = triples_to_left_args(triples)
    right_args = triples_to_right_args(triples)
    pack_length = len(run)

    # start building instructions for the run
    run_instrs = []

    # translate left args of run to vector
    left_vec_name = None
    match_params = partially_matches(left_args, previously_computed_packs)
    if left_args in previously_computed_packs:
        left_vec_name = previously_computed_packs[left_args]
    elif match_params[0]:
        left_vec_name = build_arg_vector_partial_match(match_params, run_instrs,
                                                       previously_computed_constants, left_args)
    else:
        # left args fail to match a prior computed pack. Create a new vector pack
        left_vec_name = build_arg_vector(run_instrs, pack_length,
                                         previously_computed_constants, left_args)

    # add left vector to previously computed vector
    previously_computed_packs[left_args] = left_vec_name

    assert left_vec_name != None

    # translate right args of run to vector
    right_vec_name = None
    match_params = partially_matches(right_args, previously_computed_packs)
    if right_args in previously_computed_packs:
        right_vec_name = previously_computed_packs[right_args]
    elif match_params[0]:
        right_vec_name = build_arg_vector_partial_match(match_params, run_instrs,
                                                        previously_computed_constants, right_args)
    else:
        # right args fail to match a prior computed pack. Create a new vector pack
        right_vec_name = build_arg_vector(run_instrs, pack_length,
                                          previously_computed_constants, right_args)

    # add right vector to previously computed vector
    previously_computed_packs[right_args] = right_vec_name

    assert right_vec_name != None

    # build the actual vector operation
    vec_result_name = gen_result_vector_var()
    vec_op_instr = build_vecbinop(
        vec_result_name, left_vec_name, right_vec_name, vec_op_type)
    run_instrs.append(vec_op_instr)

    # add dests vector to previously computed vector
    dests = triples_to_dests(triples)
    previously_computed_packs[dests] = vec_result_name

    # extract elements from the result vector
    # this is necessary because after DCE was run, every vector element should be used somewhere!
    destruct_result_vector(vec_result_name, dests,
                           previously_computed_constants, run_instrs)

    # finish updating run_to_packs
    run_to_packs[run_idx] = run_instrs

    # recurse to finish
    return walk_and_build_packs(runs[1:], previously_computed_packs, previously_computed_constants, run_idx + 1, run_to_packs)


def lvn_slp_basic_block(basic_block_instrs):
    """
    Perform SLP on a basic block

    Assumes code is in SSA form
    Assumes LVN and DCE have been run already
    """
    # build run of vectorizable instruction
    runs = build_runs(basic_block_instrs)

    # generate instructions for every run
    run_to_packs = walk_and_build_packs(runs, dict(), dict(), 0, dict())

    # begin stitching together the basic block with vector instructions
    # grab last instruction of every run
    last_instrs_map = last_instrs_of_runs(runs)

    # build the new basic block
    packed_basic_block_instrs = []
    # insert the new packed instructions for every run
    for instr in basic_block_instrs:
        instr_id = id(instr)
        if instr_id in last_instrs_map:
            run_idx = last_instrs_map[instr_id]
            assert run_idx in run_to_packs
            packed_basic_block_instrs += run_to_packs[run_idx]
        else:
            packed_basic_block_instrs.append(instr)

    # grab all instrucitons in runs
    all_instrs = all_instrs_in_runs(runs)

    # delete original run instructions
    final_basic_block_instrs = []
    for instr in packed_basic_block_instrs:
        instr_id = id(instr)
        if instr_id not in all_instrs:
            final_basic_block_instrs.append(instr)

    return final_basic_block_instrs


def lvn_slp_func(func):
    cfg = form_cfg_w_blocks(func)
    for basic_block in cfg:
        new_instrs = lvn_slp_basic_block(
            cfg[basic_block][INSTRS])
        cfg[basic_block][INSTRS] = new_instrs

    final_instrs = join_cfg(cfg)
    func[INSTRS] = final_instrs
    return func


def lvn_slp_prog(prog):
    ssa_prog = bril_to_ssa(prog)
    for func in ssa_prog[FUNCTIONS]:
        lvn_slp_func(func)
    bril_prog = ssa_to_bril(ssa_prog)
    return bril_prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After LVN-style SLP Vectorization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = lvn_slp_prog(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
