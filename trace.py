"""
Trace Based Optimizer for Ahead of Time Trace Optimization

Simplication of JIT to do everything on a trace AOT.

TODO: Change tracing to take arbitray end points
Current traces entire execution!
"""
import click
import sys
import json


from bril_speculation_constants import *
from bril_speculation_utilities import *
from bril_core_constants import *
from bril_core_utilities import *
from bril_memory_extension_utilities import is_mem


def trace(instrs: list) -> list:
    # check trace for memory instructions, print instructions or other side effects
    # bail if found
    for instr in instrs:
        if is_mem(instr) or is_print(instr):
            return []

    final_instrs = []
    spec_instr = build_speculate()
    final_instrs.append(spec_instr)
    for instr in instrs:
        if is_jmp(instr):
            continue
        elif is_br(instr):
            pass
        else:
            final_instrs.append(instr)
    commit_instr = build_commit()
    final_instrs.append(commit_instr)
    return final_instrs


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Trace Optimization.')
def main(pretty_print):
    trace_fp = open("trace.json", "r")
    trace_file = json.load(trace_fp)
    trace_fp.close()
    program = json.load(sys.stdin)

    if bool(pretty_print) == True:
        print(json.dumps(trace_file, indent=4, sort_keys=True))
    new_instrs = trace(trace_file["instrs"])
    print(new_instrs)
    if bool(pretty_print) == True:
        print(json.dumps(trace_file, indent=4, sort_keys=True))
    # print(json.dumps(trace_file))


if __name__ == "__main__":
    main()
