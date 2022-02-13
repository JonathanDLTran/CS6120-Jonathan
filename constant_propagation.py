import sys
import json
import click


def transfer(in_block, block):
    assert type(in_block) == set
    assert type(block) == list
    pass


def merge(blocks):
    pass


def constant_prop_func(function):
    pass


def constant_prop(program):
    pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    constant_prop(prog)


if __name__ == "__main__":
    main()
