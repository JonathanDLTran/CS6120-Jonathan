"""
Randomly Generates Well-Formed Core-Bril programs

To be used for compiler fuzzing tests.

Workflow is:
1. Generate Random CSmith Program (with print statements of variables)
2. Run Random program on reference interpreter
3. Compare results of running random program on rerference interpeter,
after transformation pass
(Can use md5 checksum to compare, as CSmith does.)

Kind of the same idea as CSmith, except much simpler,
and we have a (hopefully) correct reference interpreter
to check the result of the untransformed and transformed programs

Can you randomly generate a CFG/Dataflow graph, and then fill in the details?
Perhaps?
"""
import json
import click
from random import randint

from bril_core_constants import *


MAIN = "main"


MAX_INT = 2 ** 20
MAX_INSTRS_PER_FUNC = 100
MAX_FUNCS = 5

RANDOM_VAR_PREFIX = "random_var"
RANDOM_VAR_INDEX = 0

RANDOM_LABEL_PREFIX = "random.label"
RANDOM_LABEL_INDEX = 0


def gen_op(bril_ops):
    assert type(bril_ops) == list
    randi = randint(0, len(bril_ops) - 1)
    return bril_ops[randi]


def gen_typ(bril_types):
    assert type(bril_types) == list
    randi = randint(0, len(bril_types) - 1)
    return bril_types[randi]


def gen_bool():
    randi = randint(0, 1)
    if randi == 0:
        return False
    return True


def gen_int():
    randi = randint(-MAX_INT, MAX_INT)
    return randi


def gen_var():
    global RANDOM_VAR_INDEX
    RANDOM_VAR_INDEX += 1
    return f"{RANDOM_VAR_PREFIX}_{RANDOM_VAR_INDEX}"


def gen_label():
    global RANDOM_LABEL_INDEX
    RANDOM_LABEL_INDEX += 1
    return f".{RANDOM_LABEL_PREFIX}.{RANDOM_LABEL_INDEX}"


def exists_var_type(variables, typ):
    vars_of_correct_typ = []
    for v, t in variables:
        if t == typ:
            vars_of_correct_typ.append(v)
    return vars_of_correct_typ != []


def choose_var(variables, typ):
    vars_of_correct_typ = []
    for v, t in variables:
        if t == typ:
            vars_of_correct_typ.append(v)
    randi = randint(0, len(vars_of_correct_typ) - 1)
    return vars_of_correct_typ[randi]


def choose_label(labels):
    randi = randint(0, len(labels) - 1)
    return labels[randi]


def gen_instr(bril_ops, bril_types, variables, labels):
    """
    Generates Random Instruction or Returns None if it cannot be generated
    in the circumstances
    """
    assert type(bril_ops) == list
    assert type(bril_types) == list
    assert type(variables) == list
    assert type(labels) == list

    op = gen_op(bril_ops)
    typ = gen_typ(bril_types)
    if op == CONST:
        var = gen_var()
        if typ == INT:
            return (var, INT), {DEST: var, TYPE: INT, OP: CONST, VALUE: gen_int()}
        elif typ == BOOL:
            return (var, BOOL), {DEST: var, TYPE: BOOL, OP: CONST, VALUE: gen_bool()}
        raise RuntimeError(f"Unmatched Bril Type {typ}")
    elif op in [ADD, SUB, MUL, DIV]:
        if not exists_var_type(variables, INT):
            return None
        var1 = choose_var(variables, INT)
        var2 = choose_var(variables, INT)
        new_var = gen_var()
        output_var = choose_var(variables + [(new_var, INT)], INT)
        return (output_var, INT), {DEST: output_var, TYPE: INT, OP: op, ARGS: [var1, var2]}
    elif op in [EQ, LT, GT, LE, GE]:
        if not exists_var_type(variables, INT):
            return None
        var1 = choose_var(variables, INT)
        var2 = choose_var(variables, INT)
        new_var = gen_var()
        output_var = choose_var(variables + [(new_var, BOOL)], BOOL)
        return (output_var, BOOL), {DEST: output_var, TYPE: BOOL, OP: op, ARGS: [var1, var2]}
    elif op == NOT:
        if not exists_var_type(variables, BOOL):
            return None
        var1 = choose_var(variables, BOOL)
        new_var = gen_var()
        output_var = choose_var(variables + [(new_var, BOOL)], BOOL)
        return (output_var, BOOL), {DEST: output_var, TYPE: BOOL, OP: op, ARGS: [var1]}
    elif op in [AND, OR]:
        if not exists_var_type(variables, BOOL):
            return None
        var1 = choose_var(variables, BOOL)
        var2 = choose_var(variables, BOOL)
        new_var = gen_var()
        output_var = choose_var(variables + [(new_var, BOOL)], BOOL)
        return (output_var, BOOL), {DEST: output_var, TYPE: BOOL, OP: op, ARGS: [var1, var2]}
    elif op == JMP:
        if labels == []:
            return None
        label = choose_label(labels)
        return (None, None), {OP: JMP, LABELS: [label]}
    elif op == BR:
        if labels == []:
            return None
        label1 = choose_label(labels)
        label2 = choose_label(labels)
        return (None, None), {OP: BR, LABELS: [label1, label2]}
    elif op == RET:
        return None
    elif op == LABEL:
        label = gen_label()
        return (LABEL, label), {LABEL: label}
    elif op == CALL:
        # TODO NOTE FIXME HACK BUG
        return None
    elif op == ID:
        if not exists_var_type(variables, typ):
            return None
        var1 = choose_var(variables, typ)
        new_var = gen_var()
        output_var = choose_var(variables + [(new_var, typ)], typ)
        return (output_var, typ), {DEST: output_var, TYPE: typ, OP: op, ARGS: [var1]}
    elif op == PRINT:
        if not exists_var_type(variables, typ):
            return None
        var1 = choose_var(variables, typ)
        return (None, None), {OP: PRINT, ARGS: [var1]}
    elif op == NOP:
        return (None, None), {OP: NOP}
    elif op == PHI:
        # DO NOT HANDLE PHI NODES
        return None
    raise RuntimeError(f"Unmatched Bril Instruction Operation {op}")


def gen_function(name):
    """
    Generates a function
    """
    variables = []
    labels = []
    instrs = []
    num_instrs = randint(1, MAX_INSTRS_PER_FUNC)
    i = num_instrs
    while i > 0:
        result = gen_instr(BRIL_CORE_INSTRS +
                           [LABEL], BRIL_CORE_TYPES, variables, instrs)
        if result != None:
            i -= 1
            (var, typ), instr = result
            if var == None:
                pass
            elif var == LABEL:
                labels.append(typ)
            else:
                variables.append((var, typ))
            instrs.append(instr)
    return instrs


def gen_program():
    num_functions = randint(1, MAX_FUNCS)
    for i in range(num_functions):
        if i == 0:
            instrs = gen_function(MAIN)
            print(instrs)
    return dict()


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Randomly Generated Program.')
def main(pretty_print):
    prog = gen_program()
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
