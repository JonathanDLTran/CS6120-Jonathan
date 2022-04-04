"""
Simple Loop Fusion

Loops can be fused if they iterate the same number of times (e.g. conditions are identical)
And interleaving the orders does not change the computation or intrduce side effects

In particular, we expect that if 
a;a;a; b;b;b
then a;b;a;b;a;b as well
"""

import json
import sys
import click

from dominator_utilities import get_natural_loops
from bril_core_constants import *
from bril_core_utilities import *


def loop_fuse_loop():
    pass


def loop_fuse_func(func):
    pass


def loop_fuse(prog):
    for func in prog[FUNCTIONS]:
        pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
@click.option('--fusion', default=False, help='Perform Loop Fusion.')
def main(fusion, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    pass


if __name__ == "__main__":
    main()
