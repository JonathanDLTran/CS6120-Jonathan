"""
Aggresively Inline Every Possible Function into a main function
"""

from copy import deepcopy
from re import L
import click
import sys
import json

from bril_core_constants import *
from bril_core_utilities import *


LABEL_SUFFIX = "inlined"
LABEL_SUFFIX_COUNTER = 0

RETURN_LOC = "return.loc"
RETURN_LOC_COUNTER = 0

RET_VAR = "return_var"
RET_VAR_COUNTER = 0


def generate_new_counter():
    global LABEL_SUFFIX_COUNTER
    LABEL_SUFFIX_COUNTER += 1
    return LABEL_SUFFIX_COUNTER


def generate_new_label(label, suffix_count):
    assert type(label) == str
    return f"{label}.{LABEL_SUFFIX}.{suffix_count}"


def generate_new_var(var, suffix_count):
    assert type(var) == str
    return f"{var}_{suffix_count}_{LABEL_SUFFIX}"


def generate_new_return_loc():
    global RETURN_LOC_COUNTER
    RETURN_LOC_COUNTER += 1
    return f"{RETURN_LOC}.{RETURN_LOC_COUNTER}"


def generate_unique_exit_ret_var():
    global RET_VAR_COUNTER
    RET_VAR_COUNTER += 1
    return f"{RET_VAR}.{RET_VAR_COUNTER}.UNIQUE"


def modify_all_vars_and_args_and_labels(func, func_counter):
    for instr in func[INSTRS]:
        if DEST in instr:
            old_dest = instr[DEST]
            new_dest = generate_new_var(old_dest, func_counter)
            instr[DEST] = new_dest
        if ARGS in instr:
            old_args = instr[ARGS]
            new_args = []
            for old_arg in old_args:
                new_arg = generate_new_var(old_arg, func_counter)
                new_args.append(new_arg)
            instr[ARGS] = new_args
        if LABEL in instr:
            old_label = instr[LABEL]
            new_label = generate_new_label(old_label, func_counter)
            instr[LABEL] = new_label
        if LABELS in instr:
            old_labels = instr[LABELS]
            new_labels = []
            for old_label in old_labels:
                new_label = generate_new_label(old_label, func_counter)
                new_labels.append(new_label)
            instr[LABELS] = new_labels

    if ARGS in func:
        args = func[ARGS]
        for a in args:
            old_name = a[NAME]
            new_name = generate_new_var(old_name, func_counter)
            a[NAME] = new_name


def add_new_unique_exit(func, unique_exit_name, new_ret_var_name):
    func[INSTRS].append(build_label(unique_exit_name))

    new_instrs = []
    has_ret_var = False
    for instr in func[INSTRS]:
        if is_ret(instr) and ARGS in instr:
            ret_arg_name = instr[ARGS][0]
            new_id = build_id(
                new_ret_var_name, "Unknown_Type:From_Ret", ret_arg_name)
            new_instrs.append(new_id)
            new_jmp = build_jmp(unique_exit_name)
            new_instrs.append(new_jmp)

            has_ret_var = True
        elif is_ret(instr) and ARGS not in instr:
            new_jmp = build_jmp(unique_exit_name)
            new_instrs.append(new_jmp)
        else:
            new_instrs.append(instr)
    func[INSTRS] = new_instrs

    return has_ret_var


def inline_from_into(func1_name, func1, func2_name, func2):
    """
    Inline function 1 into function2, ASSUMING it is possible
    """

    # grab call sites of func1 in func2
    func1_call_sites = set()
    for instr in func2[INSTRS]:
        if is_call(instr) and instr[FUNCS][0] == func1_name:
            func1_call_sites.add(id(instr))

    # iterate over every call site of func1 in func2
    new_func2_instrs = []
    old_func2_instrs = func2[INSTRS]
    for instr in old_func2_instrs:
        if id(instr) not in func1_call_sites:
            new_func2_instrs.append(instr)
            continue

        # copy func1 in its entirety
        func1copy = deepcopy(func1)

        # then change all of func1's variables to be unique, includign its arguments
        # and then change all of func1's labels to be unique
        func1_counter = generate_new_counter()
        modify_all_vars_and_args_and_labels(func1copy, func1_counter)

        # force all of func1's return locations to exit out of a single position
        unique_exit_name = generate_new_return_loc()
        new_ret_var_name = generate_unique_exit_ret_var()
        has_ret_var = add_new_unique_exit(
            func1copy, unique_exit_name, new_ret_var_name)

        # stitch args from func2 into func1
        assert is_call(instr)
        if ARGS in instr:
            func2_args = instr[ARGS]
            func1_params = func1copy[ARGS]
            assert len(func1_params) == len(func2_args)

            for (f1param, f2arg) in zip(func1_params, func2_args):
                id_instr = build_id(f1param[NAME], f1param[TYPE], f2arg)
                new_func2_instrs.append(id_instr)

        # copy func1 body into func2
        new_func2_instrs += func1copy[INSTRS]

        # stitch return from func1 into func 2
        if has_ret_var:
            ret_dest = instr[DEST]
            id_instr = build_id(ret_dest, instr[TYPE], new_ret_var_name)
            new_func2_instrs.append(id_instr)

    func2[INSTRS] = new_func2_instrs

    return func2


def build_call_graph(prog):
    edges = []  # pairs of (callee, caller)
    vertices = []
    for func in prog[FUNCTIONS]:
        current_func_name = func[NAME]
        vertices.append(current_func_name)
        for instr in func[INSTRS]:
            if is_call(instr):
                other_func_name = instr[FUNCS][0]
                edges.append((other_func_name, current_func_name))
    return (vertices, edges)


def topological_sort(graph):
    vertices, edges = graph
    topological_sort_list = []
    while True:
        for vertex in vertices:
            has_no_incoming_edges = True
            for (callee, caller) in edges:
                if caller == vertex:
                    has_no_incoming_edges = False

            if has_no_incoming_edges:
                new_edges = []
                for (callee, caller) in edges:
                    if callee != vertex:
                        new_edges.append((callee, caller))
                edges = new_edges

                topological_sort_list.append(vertex)

                new_vertices = []
                for v in vertices:
                    if v != vertex:
                        new_vertices.append(v)
                vertices = new_vertices

                break

        else:
            if vertices != []:
                topological_sort_list.append(tuple(vertices))
            break

    return topological_sort_list


def called_by(func, call_graph):
    _, edges = call_graph
    called_by_lst = []
    for (callee, caller) in edges:
        if callee == func:
            called_by_lst.append(caller)
    return called_by_lst


def inline(prog):
    call_graph = build_call_graph(prog)
    sorted_funcs = topological_sort(call_graph)
    funcs = prog[FUNCTIONS]
    for callee_func_name in sorted_funcs:
        # irreducible
        if type(callee_func_name) == tuple:
            continue

        call_by_list = called_by(callee_func_name, call_graph)
        for caller_func_name in call_by_list:
            caller_func = None
            for func in funcs:
                if func[NAME] == caller_func_name:
                    caller_func = func
            assert caller_func != None

            callee_func = None
            for func in funcs:
                if func[NAME] == callee_func_name:
                    callee_func = func
            assert callee_func != None
            inline_from_into(callee_func_name, callee_func,
                             caller_func_name, caller_func)

    return prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Inlining.')
def main(pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = inline(prog)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
