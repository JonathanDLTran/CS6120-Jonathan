"""
Implementation of Larsen and Amarasingh's SLP paper from PLDI '00

I've chosen a bit of a different approach here I'm going to identify longest
runs of code that are isomorphic and independent

From that longest run, I go forward and backward usign use-def and def-use
chains as Larsen and Amarasingh do.

Then I generate vector instructions for these packs. The packs are generated in a 
topological order. There is guaranteed to be a topological ordering assuming there
are no phi-nodes.

I am going to try to use a vector pack as many times as possible, to avoid loading
and unloading to and from vector packs. This is the main difference when compared
to naive vectorization, which does not attempt to reuse packs at all.
"""

import click
import sys
import json


def topological_sort():
    pass


def slp_prog(prog):
    pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After SLP Vectorization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = slp_prog(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
