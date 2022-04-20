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
from bril_float_utilities import is_float

from lvn import lvn


BAILOUT_LABEL = "bailout.label"
FINISH_LABEL = "finish.label"

GUARD_VAR = "guard_var"

LVN_FUNC = "lvn_func"


def trace(instrs: list) -> list:
    # check trace for memory instructions, print instructions or other side effects
    # bail if found
    for instr_pair in instrs:
        instr = instr_pair["instr"]
        if is_mem(instr) or is_print(instr):
            raise RuntimeError("Should not have mem or print instructions")

    final_instrs = []
    spec_instr = build_speculate()
    final_instrs.append(spec_instr)
    for instr_pair in instrs:
        instr = instr_pair["instr"]
        if is_jmp(instr):
            continue
        elif is_br(instr):
            br_cond = instr_pair["branch"]
            assert type(br_cond) == bool
            if br_cond:
                guard_instr = build_guard(instr[ARGS][0], BAILOUT_LABEL)
                final_instrs.append(guard_instr)
            else:
                # get false branch of br instr for guard and jump to BAILOUT_LABEL
                guard_negation = {DEST: GUARD_VAR, OP: NOT,
                                  TYPE: BOOL, ARGS: [instr[ARGS][0]]}
                final_instrs.append(guard_negation)
                guard_instr = build_guard(GUARD_VAR, BAILOUT_LABEL)
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
    end_offset = trace_file["end_offset"]
    end_func = trace_file["end_func"]
    assert (start_func == end_func)

    if end_func == "":
        end_func = MAIN
    if end_offset < 0:
        # find end of main function
        for func in funcs:
            if func[NAME] == MAIN:
                end_offset = len(func[INSTRS])
    if start_func == "":
        start_func = MAIN

    assert (start_func == end_func)
    if start_func == MAIN:
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
            instrs = optimize(trace_instrs) + instrs

            func[INSTRS] = instrs
    return program


def call_lvn(trace_instrs):
    # check if float instructions are in there, and bail if so
    for instr in trace_instrs:
        if is_float(instr):
            return trace_instrs

    # grab free vars in trace_instrs and make them arguments
    free_vars = set()
    defined_vars = set()
    for instr in trace_instrs:
        if ARGS in instr:
            for a in instr[ARGS]:
                if a not in defined_vars:
                    free_vars.add(a)
        if DEST in instr:
            defined_vars.add(instr[DEST])

    args = []
    for a in free_vars:
        args.append({NAME: a, TYPE: INT})  # fake a type

    prog = {}
    function = {}
    function[INSTRS] = trace_instrs
    function[NAME] = LVN_FUNC
    function[ARGS] = args
    prog[FUNCTIONS] = [function]

    optimized_prog = lvn(prog)

    new_trace_instrs = optimized_prog[FUNCTIONS][0][INSTRS]

    return new_trace_instrs


def optimize(trace_instrs):
    return call_lvn(trace_instrs)


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Trace Optimization.')
def main(pretty_print):
    program_dict = json.load(sys.stdin)
    program = program_dict["prog"]
    trace_file = program_dict["trace"]

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
