"""
Implementation of Larsen and Amarasingh's SLP paper from PLDI '00

I've chosen a bit of a different approach here I'm going to identify longest
runs of code that are isomorphic and independent

From that longest run, I go forward and backward usign use-def and def-use
chains as Larsen and Amarasingh do.

Then I generate vector instructions for these packs. The packs are generated in a
topological order. There is guaranteed to be a topological ordering assuming there
are no phi-nodes.

I am going to try to use a vector pack as many times as possible, to avoid loading
and unloading to and from vector packs. This is the main difference when compared
to naive vectorization, which does not attempt to reuse packs at all.
"""

import click
from itertools import combinations
import json
import sys

from bril_core_constants import *
from bril_core_utilities import *

from cfg import form_cfg_w_blocks, join_cfg

from ssa import bril_to_ssa, ssa_to_bril

from vectorization_utilities import *


UNDEFINED = "undefined"
UNDEFINED_INSTR = {
    ARGS: [UNDEFINED, UNDEFINED],
    DEST: UNDEFINED,
    TYPE: UNDEFINED,
    OP: UNDEFINED,
}


MAX_NUM_RUNS = 5


def filter_undefined_packs(vector_packs):
    new_vector_packs = []
    for vector_perm in vector_packs:
        new_vector_perm = []
        for pack_pair in vector_perm:
            all_undefined = True
            for (fst, snd) in pack_pair:
                if fst != UNDEFINED or snd != UNDEFINED:
                    all_undefined = False
            if not all_undefined:
                new_vector_perm.append(pack_pair)
        new_vector_packs.append(new_vector_perm)
    return new_vector_packs


def generate_cartesian_product_of_combinations(vector_perms):
    """
    Generate Cartesian Product of Combinations, with each element of a tuple representing the packing for each run

    Incredibly Expensive when the length of vector_perms is large
    """
    if len(vector_perms) == 0:
        return []
    elif len(vector_perms) == 1:
        first_vector_of_permutations = vector_perms[0]
        return list(map(lambda e: [e], first_vector_of_permutations))

    final_perms = []
    first_vector_of_permutations = vector_perms[0]
    remainder_permutations = generate_cartesian_product_of_combinations(
        vector_perms[1:])
    for perm in first_vector_of_permutations:
        for remainder_vector_perm in remainder_permutations:
            new_perm = [perm] + remainder_vector_perm
            final_perms.append(new_perm)

    # # calculate minimum number of repeats
    # maximum_repeats = 1000
    # for perm in final_perms:
    #     new_len = len(set(perm))
    #     if new_len < maximum_repeats:
    #         maximum_repeats = new_len

    # # do some filtering on minimum number of repeats
    # max_perms = []
    # for perm in final_perms:
    #     new_len = len(set(perm))
    #     if new_len == maximum_repeats:
    #         max_perms.append(perm)

    return final_perms


def brute_force_alignment_vec_size(runs):
    # TODO Handle Runs size less than or equal to 5
    assert len(runs) <= MAX_NUM_RUNS

    # pad each run with undefined variables to bring it to VECTOR_WIDTH
    padded_runs = []
    for run in runs:
        padded_run = []
        assert len(run) <= VECTOR_LANE_WIDTH
        for instr in run:
            padded_run.append(instr)
        for _ in range(VECTOR_LANE_WIDTH - len(run)):
            padded_run.append(UNDEFINED_INSTR)
        padded_runs.append(padded_run)
    assert len(padded_runs) == len(runs) <= MAX_NUM_RUNS

    packed_pairs = []
    for run in padded_runs:
        left_vec = []
        right_vec = []
        assert len(run) == VECTOR_LANE_WIDTH
        for instr in run:
            assert ARGS in instr
            args = instr[ARGS]
            assert len(args) == 2
            left_vec.append(args[0])
            right_vec.append(args[1])
        packed_pairs.append(list(zip(left_vec, right_vec)))
    assert len(packed_pairs) == len(padded_runs) == len(runs) <= MAX_NUM_RUNS

    # generate all combinations of vector pack members
    packed_pair_combinations = []
    for vector_pair in packed_pairs:
        combination_options = []
        # choose 2, 3, ... VECTOR_LANE_WIDTH of elements as a pack
        for i in range(2, VECTOR_LANE_WIDTH + 1):
            combination_of_packs = combinations(vector_pair, i)
            combination_options += list(combination_of_packs)
        packed_pair_combinations.append(combination_options)
    assert len(packed_pair_combinations) == len(packed_pairs) == len(
        padded_runs) == len(runs) <= MAX_NUM_RUNS

    # filter out all packs that are clearly all undefined!
    no_undefined_packs = filter_undefined_packs(packed_pair_combinations)

    # generate final pack candidates
    final = generate_cartesian_product_of_combinations(no_undefined_packs)


def slp_basic_block(basic_block_instrs):
    """
    Perform SLP on a basic block
    """
    # build run of vectorizable instruction
    runs = build_runs(basic_block_instrs)

    # brute force enumerate every possible alignment and vector size, given the runs
    brute_force_alignment_vec_size(runs)


def slp_func(func):
    cfg = form_cfg_w_blocks(func)
    for basic_block in cfg:
        new_instrs = slp_basic_block(
            cfg[basic_block][INSTRS])
        cfg[basic_block][INSTRS] = new_instrs

    final_instrs = join_cfg(cfg)
    func[INSTRS] = final_instrs
    return func


def slp_prog(prog):
    ssa_prog = bril_to_ssa(prog)
    for func in ssa_prog[FUNCTIONS]:
        slp_func(func)
    bril_prog = ssa_to_bril(ssa_prog)
    return bril_prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After SLP Vectorization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = slp_prog(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
