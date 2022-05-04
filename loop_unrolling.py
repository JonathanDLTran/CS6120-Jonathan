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


-------------

In basic unrolling, a natural loop is taken. We only consider loops that enter
and exit through the header of the natural loop, e.g. only single entry and exit
loops.

The branch MUST be in the header. The branch condition must be some affine combination
of integer based varaibles, e.g. ai + b 

The body of the loop must have an update on i in ONE place.

We also forbid side effects in the loop like print statements or function calls.

For this type of loop, we can immediately solve out how many iterations the loop should 
execute. We can then fully unroll the loop, and add the remainder at the end.

We can do a "cheaper" unroll for something like a while loop as well. Wikipedia
documents an unroll that keeps in branches. It would be nice to eliminate these branches
but sometimes there is no easy way. Perhaps that is where synthesis can be used.
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
