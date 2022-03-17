"""
Implementation of Induction Variable Elimination for Loops 
TODO
"""

import sys
import json
import click


def func_induction_variables(): pass


def induction_varaibles(): pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
@click.option('--ive', default=False, help='Pretty Print Original Program.')
def main(pretty_print, ive):
    prog = json.load(sys.stdin)
    print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
