"""
Basic Loop Unrolling

TODO: How to identify loops that can be unrolled (e.g. a for loop)
IDEA: Can we feed the loop to a synthesizer sketch with the sketch already
being partly unrolled??

The sketch would have to be built around the Bril language though, or you 
would have to build your own sketcher.
"""

import json
import sys
import click


def unroll():
    pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    unroll()
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
