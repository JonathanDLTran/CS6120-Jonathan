import sys
import json
import click


def pass_routine(program):
    for func in program["functions"]:
        for instr in func["instrs"]:
            pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
