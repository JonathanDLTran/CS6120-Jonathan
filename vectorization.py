"""
Automatic Vectorization

TODO
- First: preprocess: If __No-Mem Ops__, then run DCE, LVN and LICM  [AVOID ADCE/GVN because they use ssa and this actually makes less improvement]
- Second: run alias analysis if there are Mem Ops
- Third: Loop Unroll as Much as Possible
- Fourth: Run Function Block Coalescing to remove as many labels and jumps
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
from lvn import lvn
from licm import licm_main
from alias_analysis import alias_analysis
from loop_unrolling import fully_unroll_prog


def preprocess_prog(prog):
    """
    Preprocess Program, if possible

    Ignore programs with Memory Ops, but do unrolling to all programs
    """
    # do preprocessing, if possible, with no memory ops
    preprocessed_prog = prog 
    if not has_mem_ops(prog):
        dce_prog = dce(prog, "True", "True", "False", "False")
        lvn_prog = lvn(dce_prog)
        licm_prog = licm_main(lvn_prog)
        preprocessed_prog = licm_prog
    unrolled_prog = fully_unroll_prog(preprocessed_prog)
    return unrolled_prog


def vectorize_prog(prog):
    """
    Vectorizes prog
    TODO
    """
    preprocessed_prog = preprocess_prog(prog)


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Vectorization.')
@click.option('--vectorize', default=False, help='Vectorize.')
def main(pretty_print, vectorize):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = prog
    if bool(vectorize) == True:
        final_prog = vectorize_prog(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))

if __name__ == "__main__":
    main()