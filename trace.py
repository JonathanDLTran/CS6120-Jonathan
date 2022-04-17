"""
Trace Based Optimizer for Ahead of Time Trace Optimization

Simplication of JIT to do everything on a trace AOT.

TODO: Change tracing to take arbitray end points
Current traces entire execution!
"""
import click
import sys
import json


def trace(instrs: list):
    for instr in instrs:
        pass


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Trace Optimization.')
def main(pretty_print):
    instrs = json.load(sys.stdin)
    if bool(pretty_print) == True:
        print(json.dumps(instrs, indent=4, sort_keys=True))
    if bool(pretty_print) == True:
        print(json.dumps(instrs, indent=4, sort_keys=True))
    # print(json.dumps(instrs))


if __name__ == "__main__":
    main()
