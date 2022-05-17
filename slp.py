"""
Implementation of Larsen and Amarasingh's SLP paper from PLDI '00
"""

import click
import sys
import json


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