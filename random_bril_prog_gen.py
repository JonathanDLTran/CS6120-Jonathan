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
import copy
from random import randint

from random_cfg import gen_cfg, CFGNode

from bril_core_constants import *
from bril_core_utilities import *


MAIN = "main"


MAX_INT = 2 ** 20
MAX_INSTRS_PER_BASIC_BLOCK = 10
MAX_ARGS_PER_FUNCTION = 3
MAX_FUNCS = 5
MAX_NODES_PER_CFG = 10

RANDOM_ARG_PREFIX = "random_arg"
RANDOM_ARG_INDEX = 0

RANDOM_VAR_PREFIX = "random_var"
RANDOM_VAR_INDEX = 0

BRANCH_VAR_PREFIX = "branch_var"
BRANCH_VAR_INDEX = 0

RANDOM_LABEL_PREFIX = "random.label"
RANDOM_LABEL_INDEX = 0


def gen_typ():
    randi = randint(0, len(BRIL_CORE_TYPES) - 1)
    return BRIL_CORE_TYPES[randi]


def gen_bool():
    randi = randint(0, 1)
    if randi == 0:
        return False
    return True


def gen_int():
    randi = randint(-MAX_INT, MAX_INT)
    return randi


def gen_arg():
    global RANDOM_ARG_INDEX
    RANDOM_ARG_INDEX += 1
    return f"{RANDOM_ARG_PREFIX}_{RANDOM_ARG_INDEX}"


def gen_var():
    global RANDOM_VAR_INDEX
    RANDOM_VAR_INDEX += 1
    return f"{RANDOM_VAR_PREFIX}_{RANDOM_VAR_INDEX}"


def gen_branch_var():
    global BRANCH_VAR_INDEX
    BRANCH_VAR_INDEX += 1
    return f"{BRANCH_VAR_PREFIX}_{BRANCH_VAR_INDEX}"


def gen_label():
    global RANDOM_LABEL_INDEX
    RANDOM_LABEL_INDEX += 1
    return f"{RANDOM_LABEL_PREFIX}.{RANDOM_LABEL_INDEX}"


def exists_var_type(variables, typ):
    vars_of_correct_typ = []
    for v, t in variables.items():
        if t == typ:
            vars_of_correct_typ.append(v)
    return vars_of_correct_typ != []


def choose_var(variables, typ):
    vars_of_correct_typ = []
    for v, t in variables.items():
        if t == typ:
            vars_of_correct_typ.append(v)
    if vars_of_correct_typ == []:
        raise RuntimeError(f"No variable of correct type {typ} found.")
    randi = randint(0, len(vars_of_correct_typ) - 1)
    return vars_of_correct_typ[randi]


def gen_comp_instr(op, output_var, live_var2typ):
    assert op in COMP_OPS
    arg1 = choose_var(live_var2typ, INT)
    arg2 = choose_var(live_var2typ, INT)
    if op == EQ:
        return build_eq(output_var, arg1)
    op2builder = {
        LT: build_lt,
        GT: build_gt,
        LE: build_le,
        GE: build_ge,
    }
    builder = op2builder[op]
    return builder(output_var, arg1, arg2)


def gen_int_instr(op, output_var, live_var2typ):
    assert op in INT_OPS
    arg1 = choose_var(live_var2typ, INT)
    arg2 = choose_var(live_var2typ, INT)
    op2builder = {
        ADD: build_add,
        SUB: build_sub,
        MUL: build_mul,
        DIV: build_div,
    }
    builder = op2builder[op]
    return builder(output_var, arg1, arg2)


def gen_bool_instr(op, output_var, live_var2typ):
    assert op in LOGIC_OPS
    arg1 = choose_var(live_var2typ, BOOL)
    arg2 = choose_var(live_var2typ, BOOL)
    if op == NOT:
        return build_not(output_var, arg1)
    op2builder = {
        AND: build_and,
        OR: build_or,
    }
    builder = op2builder[op]
    return builder(output_var, arg1, arg2)


def gen_rand_comp_instr(output_var, live_var2typ):
    op_idx = randint(0, len(COMP_OPS) - 1)
    op = COMP_OPS[op_idx]
    return gen_comp_instr(op, output_var, live_var2typ)


def gen_rand_int_instr(output_var, live_var2typ):
    op_idx = randint(0, len(INT_OPS) - 1)
    op = INT_OPS[op_idx]
    return gen_int_instr(op, output_var, live_var2typ)


def gen_rand_bool_instr(output_var, live_var2typ):
    op_idx = randint(0, len(LOGIC_OPS) - 1)
    op = LOGIC_OPS[op_idx]
    return gen_bool_instr(op, output_var, live_var2typ)


def gen_rand_instr(output_type, output_var, live_var2typ):
    types_of_random_generators = []
    if output_type == BOOL:
        if exists_var_type(live_var2typ, BOOL):
            types_of_random_generators.append(gen_rand_bool_instr)
        if exists_var_type(live_var2typ, INT):
            types_of_random_generators.append(gen_rand_comp_instr)
    elif output_type == INT:
        if exists_var_type(live_var2typ, INT):
            types_of_random_generators.append(gen_rand_int_instr)
    else:
        raise RuntimeError(f"Unmatched output type {output_type}.")

    if types_of_random_generators == []:
        return (False, None)

    assert len(types_of_random_generators) > 0
    random_generator_idx = randint(0, len(types_of_random_generators) - 1)
    random_generator_func = types_of_random_generators[random_generator_idx]
    return (True, random_generator_func(output_var, live_var2typ))


def gen_basic_block(bb_name, neighbors, live_initialized_vars, max_basic_block_instrs=MAX_INSTRS_PER_BASIC_BLOCK):
    assert type(bb_name) == str
    assert type(neighbors) == list
    num_neighbors = len(neighbors)
    assert type(num_neighbors) == int
    assert 0 <= num_neighbors <= 2
    assert type(live_initialized_vars) == dict
    assert type(max_basic_block_instrs) == int
    assert 0 < max_basic_block_instrs <= MAX_INSTRS_PER_BASIC_BLOCK

    cloned_live_initialized_vars = copy.deepcopy(live_initialized_vars)

    actual_basic_block_instrs = randint(1, max_basic_block_instrs)
    var2typ = dict()
    for _ in range(actual_basic_block_instrs):
        var = gen_var()
        typ = gen_typ()
        var2typ[var] = typ

    bb_instrs = []

    func_label_instr = build_label(bb_name)
    bb_instrs.append(func_label_instr)

    for var, typ in var2typ.items():
        init_method = randint(0, 1)
        if init_method == 0:
            # generate a constant
            const_instr = None
            if isa_int(typ):
                const_instr = build_const(var, INT, gen_int())
            else:
                const_instr = build_const(var, BOOL, gen_bool())
            assert const_instr != None
            bb_instrs.append(const_instr)

        else:
            # try to generate an expression based on live variables
            (can_do_random, result) = gen_rand_instr(
                typ, var, cloned_live_initialized_vars)
            if can_do_random:
                bb_instrs.append(result)

            # fall back to a constant
            else:
                const_instr = None
                if isa_int(typ):
                    const_instr = build_const(var, INT, gen_int())
                else:
                    const_instr = build_const(var, BOOL, gen_bool())
                assert const_instr != None
                bb_instrs.append(const_instr)

        cloned_live_initialized_vars[var] = typ

    # generate the final branch if needed
    if num_neighbors == 2:
        bool_var_name = None
        for var, typ in cloned_live_initialized_vars.items():
            if isa_bool(typ):
                assert var != None
                bool_var_name = choose_var(cloned_live_initialized_vars, BOOL)
                break

        final_branch_instr = None
        assert len(neighbors) == 2
        [label1, label2] = neighbors

        if bool_var_name == None:
            new_bool_var = gen_branch_var()
            new_bool_init_instr = build_const(new_bool_var, BOOL, gen_bool())
            final_branch_instr = build_br(new_bool_init_instr, label1, label2)
        else:
            final_branch_instr = build_br(bool_var_name, label1, label2)

        assert final_branch_instr != None
        bb_instrs.append(final_branch_instr)

    # otherwise generate a jump if needed
    elif num_neighbors == 1:
        assert len(neighbors) == 1
        [label] = neighbors
        final_jump_instr = build_jmp(label)
        bb_instrs.append(final_jump_instr)

    return (cloned_live_initialized_vars, bb_instrs)


def gen_function(func_name, max_cfg_nodes=MAX_NODES_PER_CFG):
    """
    Generates a function

    Creates a random CFG for the function
    Fills in each CFG node with instructions
    """
    num_nodes = randint(1, max_cfg_nodes)
    cfg = gen_cfg(num_nodes)
    (entry_node, nodes) = cfg

    num_args = randint(0, MAX_ARGS_PER_FUNCTION)
    args = {gen_arg(): gen_typ() for _ in range(num_args)}
    if func_name == MAIN:
        args = {}
    live_initialized_vars = {**args}
    function_instrs = []
    for node in nodes:
        basic_block_instrs = []
        neighbor_nodes = node.get_neighbors()
        neighbors = []
        for neighbor_node in neighbor_nodes:
            neighbor_name = str(neighbor_node.get_name())
            neighbors.append(neighbor_name)
        if node == entry_node:
            name = str(node.get_name())
            (new_live_vars, basic_block_instrs) = gen_basic_block(name, neighbors,
                                                                  live_initialized_vars, MAX_INSTRS_PER_BASIC_BLOCK)
            live_initialized_vars = new_live_vars
        else:
            name = str(node.get_name())
            (_, basic_block_instrs) = gen_basic_block(name, neighbors,
                                                      live_initialized_vars, MAX_INSTRS_PER_BASIC_BLOCK)

        function_instrs += basic_block_instrs

    constructed_args = [build_arg(arg_name, arg_type)
                        for arg_name, arg_type in args.items()]
    return build_func(func_name, constructed_args, None, function_instrs)


def gen_program():
    num_functions = randint(1, MAX_FUNCS)
    function_names = [gen_label() for _ in range(num_functions - 1)] + [MAIN]
    functions = []
    for func_name in function_names:
        cfg_nodes = randint(1, MAX_NODES_PER_CFG)
        func = gen_function(func_name, cfg_nodes)
        functions.append(func)

    return build_program(functions)


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Randomly Generated Program.')
def main(pretty_print):
    prog = gen_program()
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
