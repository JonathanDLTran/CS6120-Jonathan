import json
import sys
import click

from worklist_solver import Worklist

from bril_core_constants import *
from bril_core_utilities import *


HEAP_LOC_IDX = 0


def gen_heap_loc():
    global HEAP_LOC_IDX
    HEAP_LOC_IDX += 1
    return HEAP_LOC_IDX


def merge():
    pass


def transfer():
    pass


def main():
    pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
@click.option('--aa', default=False, help='Perform Alias Analysis.')
def main(fusion, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    pass


if __name__ == "__main__":
    main()
