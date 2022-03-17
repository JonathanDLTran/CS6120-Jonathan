"""
Implementation of Induction Variable Elimination for Loops 
TODO
"""

import sys
import json
import click


def pass_routine(program):
    for func in program["functions"]:
        for instr in func["instrs"]:
            pass


@click.command()
def main():
    prog = json.load(sys.stdin)
    print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
