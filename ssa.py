import click
import sys
import json

from bril_core_constants import *


def from_ssa(program):
    pass


def to_ssa(program):
    return is_ssa(program)


def is_ssa(program):
    for func in program["functions"]:
        def_vars = set()
        if ARGS in func:
            for a in func[ARGS]:
                def_vars.add(a)
        for instr in func["instrs"]:
            if DEST in instr:
                dst = instr[DEST]
                if dst in def_vars:
                    raise RuntimeError(f"Program is not in SSA form.")
                def_vars.add(dst)
    return program


@click.command()
@click.option('--to-ssa', default=False, help='Converts Bril program to SSA from.')
@click.option('--from-ssa', default=False, help='Converts Bril program out of SSA form.')
@click.option('--pretty-print', default=False, help='Print transformed program.')
def main(to_ssa, from_ssa, pretty_print):
    prog = json.load(sys.stdin)
    if to_ssa:
        prog = to_ssa(prog)
    if from_ssa:
        prog = from_ssa(prog)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
