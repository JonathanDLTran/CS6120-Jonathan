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
from itertools import combinations, permutations
import json
import sys

from bril_core_constants import *
from bril_core_utilities import *

from cfg import form_cfg_w_blocks, join_cfg

from ssa import bril_to_ssa, ssa_to_bril

from vectorization_utilities import *


MAX_RUNS_HANDLED = 4


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


def packs_to_world_key(packs, current_world_prefix):
    assert type(packs) == list
    assert type(current_world_prefix) == tuple
    return (tuple(packs), *current_world_prefix)


def world_key_to_set(current_world_prefix):
    assert type(current_world_prefix) == tuple
    return {*current_world_prefix}


def walk_and_build_packs(precomputed_packs, runs, world_map, current_world_key):
    """
    TODO: Handle Precomputed Packs
    """
    assert len(runs) <= MAX_RUNS_HANDLED

    if len(runs) == 0:
        return

    run = runs[0]

    assert len(run) <= VECTOR_LANE_WIDTH
    triples = run_to_triples(run)
    assert len(triples) <= VECTOR_LANE_WIDTH

    run_pack_perms = []
    for i in range(2, len(triples) + 1):
        pack_perms = list(permutations(triples, i))
        run_pack_perms += pack_perms

    if len(triples) < 2:
        run_pack_perms = triples

    print(run_pack_perms)
    count = 0


def lvn_slp_basic_block(basic_block_instrs):
    """
    Perform SLP on a basic block
    """
    # build run of vectorizable instruction
    runs = build_runs(basic_block_instrs)

    walk_and_build_packs([], runs[:4], dict(), tuple())


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
