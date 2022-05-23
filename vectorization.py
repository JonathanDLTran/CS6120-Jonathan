"""
Automatic Vectorization Main Runner
Choose Between Various Vectorization Modes

TODO
- First: preprocess: If __No-Mem Ops__, then run DCE, LVN and LICM  [AVOID ADCE/GVN because they use ssa and this actually makes less improvement]
- Second: run alias analysis if there are Mem Ops
- Third: Loop Unroll as Much as Possible
- Fourth: Move Stores as far down as possible
- Fifth: Run Function Block Coalescing to remove as many labels and jumps
---------
Vectorization
- Use ideas from SLP Paper
    - Heuristic?
"""

import click
import sys
import json


from bril_core_constants import *
from bril_core_utilities import *
from bril_memory_extension_constants import *
from bril_memory_extension_utilities import *

from dce import dce
from licm import licm_main
from cfg import coalesce_prog
from loop_unrolling import fully_unroll_prog
from store_movement import move_stores_prog

from naive_vectorization import naive_vectorization_prog
from opportunistic_lvn_slp import lvn_slp_prog
from vectorization_utilities import canonicalize_prog, constant_movement


def preprocess_prog(prog):
    """
    Preprocess Program, if possible

    Ignore programs with Memory Ops, but do unrolling and coalescing to all programs
    """
    # do preprocessing, if possible, with no memory ops
    preprocessed_prog = prog
    if not has_mem_ops(prog):
        dce_prog = dce(prog, 1, 1, False, False)
        licm_prog = licm_main(dce_prog)
        preprocessed_prog = licm_prog
    canonical_prog = canonicalize_prog(preprocessed_prog)
    unrolled_prog = fully_unroll_prog(canonical_prog)
    moved_stores_prog = move_stores_prog(unrolled_prog)
    constant_moved_prog = constant_movement(moved_stores_prog)
    coalesced_prog = coalesce_prog(constant_moved_prog)
    return coalesced_prog


def vectorize_prog(prog, naive, op):
    """
    Vectorizes prog
    TODO
    """
    preprocessed_prog = preprocess_prog(prog)
    final_prog = prog
    if bool(op) == True:
        final_prog = lvn_slp_prog(preprocessed_prog)
    elif bool(naive) == True:
        final_prog = naive_vectorization_prog(preprocessed_prog)
    # No Vectorization Flags Enabled
    return final_prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Vectorization.')
@click.option('--naive', default=False, help='Naive Vectorization.')
@click.option('--op', default=False, help='Opportunistic Vectorization.')
def main(pretty_print, naive, op):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = vectorize_prog(prog, naive, op)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
