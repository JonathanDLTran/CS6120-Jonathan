"""
Trace Based Optimizer for Ahead of Time Trace Optimization

Simplication of JIT to do everything on a trace AOT.

TODO: Change tracing to take arbitray end points
Current traces entire execution!
"""
from tracemalloc import start
import click
import sys
import json


from bril_speculation_constants import *
from bril_speculation_utilities import *
from bril_core_constants import *
from bril_core_utilities import *
from bril_memory_extension_utilities import is_mem


BAILOUT_LABEL = "bailout.label"
FINISH_LABEL = "finish.label"


def trace(instrs: list) -> list:
    # check trace for memory instructions, print instructions or other side effects
    # bail if found
    for instr_pair in instrs:
        instr = instr_pair["instr"]
        if is_mem(instr) or is_print(instr):
            return []

    final_instrs = []
    spec_instr = build_speculate()
    final_instrs.append(spec_instr)
    for instr_pair in instrs:
        instr = instr_pair["instr"]
        if is_jmp(instr):
            continue
        elif is_br(instr):
            # get false branch of br instr for guard and jump to BAILOUT_LABEL
            guard_instr = build_guard(instr[ARGS][0], BAILOUT_LABEL)
            final_instrs.append(guard_instr)
        elif is_label(instr):
            continue
        else:
            final_instrs.append(instr)
    commit_instr = build_commit()
    final_instrs.append(commit_instr)
    return final_instrs


def insert_trace(program, trace_instrs, trace_file):
    funcs = program[FUNCTIONS]
    start_func = trace_file["start_func"]
    start_offset = trace_file["start_offset"]
    end_offset = trace_file["end_offset"]
    end_func = trace_file["end_func"]
    if end_func == "":
        end_func = MAIN
    if end_offset < 0:
        # find end of main function
        for func in funcs:
            if func[NAME] == MAIN:
                end_offset = len(func[INSTRS])
    if start_func == "":
        start_func = MAIN
    if start_offset < 0:
        start_offset = 0
    if start_offset == 0:
        return program
    for func in funcs:
        # get location where tracing ends
        if func[NAME] == end_func:
            instrs = func[INSTRS]
            finish_label = {LABEL: FINISH_LABEL}
            instrs.insert(end_offset, finish_label)
            func[INSTRS] = instrs
        if func[NAME] == start_func:
            instrs = func[INSTRS]

            # jump to finish
            jmp_to_finish_instr = {
                OP: JMP,
                LABELS: [FINISH_LABEL],
            }
            # bailout label
            bailout_label = {LABEL: BAILOUT_LABEL}

            trace_instrs += [jmp_to_finish_instr, bailout_label]
            for trace_instr in reversed(trace_instrs):
                instrs.insert(start_offset, trace_instr)

            func[INSTRS] = instrs
    return program


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Trace Optimization.')
def main(pretty_print):
    trace_fp = open("trace.json", "r")
    trace_file = json.load(trace_fp)
    trace_fp.close()
    program = json.load(sys.stdin)

    if bool(pretty_print) == True:
        print(json.dumps(trace_file, indent=4, sort_keys=True))

    trace_instrs = trace(trace_file["instrs"])
    # print(trace_instrs)
    new_program = insert_trace(program, trace_instrs, trace_file)

    if bool(pretty_print) == True:
        print(json.dumps(trace_file, indent=4, sort_keys=True))
    print(json.dumps(new_program))


if __name__ == "__main__":
    main()
