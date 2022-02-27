from copy import deepcopy
import click
import sys
import json

from cfg import form_blocks, join_blocks
from bril_core_constants import *


def identify_loop_invariant_instrs():
    pass


def move_loop_invariant_instrs():
    pass


def licm(program):
    """
    LICM wrapper function
    """
    pass


@click.command()
@click.option('--licm', default=False, help='Run Loop Invariant Code Motion.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(licm, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = licm(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
