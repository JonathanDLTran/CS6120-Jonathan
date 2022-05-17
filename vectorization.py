"""
Automatic Vectorization

TODO
- First: preprocess: If __No-Mem Ops__, then run DCE, GVN and LICM 
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


def vectorize_prog(prog):
    """
    Vectorizes prog
    TODO
    """
    pass


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