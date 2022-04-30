"""
Basic Loop Unrolling

TODO: How to identify loops that can be unrolled (e.g. a for loop)
IDEA: Can we feed the loop to a synthesizer sketch with the sketch already
being partly unrolled??

The sketch would have to be built around the Bril language though, or you 
would have to build your own sketcher.

The idea is given a natural loop N, you can sometimes unroll N in to a fixed degree
or completely.

Loop Header H 
Loop Bodies B 
---> 
H B B B B (N TIMES)... H B B B B (N TIMES)...

Where N is chosen appropriately large. A syntehsizer can figure out what N is
and prove that the new unrolled loop is equivalent to (H B) using an SMT equivalence
checker.
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
