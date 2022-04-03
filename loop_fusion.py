import json
import sys
import click

from bril_core_constants import *
from bril_core_utilities import *


def loop_fuse_loop():
    pass


def loop_fuse_func():
    pass


def loop_fuse(prog):
    for func in prog[FUNCTIONS]:
        pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    pass


if __name__ == "__main__":
    main()
