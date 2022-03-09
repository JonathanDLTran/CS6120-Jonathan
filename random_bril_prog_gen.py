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


MAX_INT = 2 ** 20

RANDOM_VAR_PREFIX = "random_var"
RANDOM_VAR_INDEX = 0

RANDOM_LABEL_PREFIX = "random_label"


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


def gen_instr(bril_ops, bril_types, variables):
    """
    Generates Random Instruction
    """
    assert type(bril_ops) == list
    assert type(bril_types) == list
    assert type(variables) == list

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
        pass
    elif op in [EQ, LT, GT, LE, GE]:
        pass
    elif op == NOT:
        pass
    elif op in [AND, OR]:
        pass
    elif op == JMP:
        pass
    elif op == BR:
        pass
    elif op == RET:
        pass
    elif op == CALL:
        pass
    elif op == ID:
        pass
    elif op == PRINT:
        pass
    elif op == NOP:
        pass
    elif op == PHI:
        pass
    raise RuntimeError(f"Unmatched Bril Instruction Operation {op}")


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Randomly Generated Program.')
def main(pretty_print):
    prog = dict()
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
