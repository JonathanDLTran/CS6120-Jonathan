"""
Implementation of Induction Variable Elimination for Loops

ASSSUMED NOT TO BE IN SSA FORM
"""
from copy import deepcopy
import sys
import json
import click
from collections import OrderedDict

from reaching_definitions import reaching_defs_func
from licm import insert_preheaders, identify_loop_invariant_instrs, insert_into_bb, LOOP_INVARIANT
from cfg import form_cfg_w_blocks, join_cfg, INSTRS
from dominator_utilities import get_natural_loops, get_dominators_w_cfg
from bril_core_constants import *
from bril_core_utilities import is_add, is_mul, is_const, is_int


UNIQUE_VAR_NAME = "unique_var"
UNIQUE_VAR_IDX = 0


BEFORE_I = 0
AFTER_I = 1


def gen_new_var():
    global UNIQUE_VAR_IDX
    UNIQUE_VAR_IDX += 1
    return f"{UNIQUE_VAR_NAME}_{UNIQUE_VAR_IDX}"


class InductionVariable(object):
    """
    Abstract Induction Variable Class
    """

    def __init__(self):
        pass


class BasicInductionVariable(InductionVariable):
    """
    Basic Induction Variable

    Represents i += e
    where i is a defintiion defined exactly once in the loop and e is loop invariant
    """

    def __init__(self, i_id, i, e, e_val, basic_block) -> None:
        self.i_id = i_id
        self.i = i
        self.e = e
        self.e_val = e_val
        self.basic_block = basic_block

    def __str__(self) -> str:
        return f"{self.i} += {self.e} @{self.i_id}"

    def __repr__(self) -> str:
        return self.__str__()


class MulInvariant(InductionVariable):
    """
    Multiplied Induction Variable
    Represents a = c * i where c is a loop invariant value and i is a basic induction variable
    """

    def __init__(self, a_id, a, c, i) -> None:
        self.a_id = a_id
        self.a = a
        self.c = c
        self.i = i

    def __str__(self) -> str:
        return f"{self.a} = {self.c} * {self.i} @{self.a_id}"

    def __repr__(self) -> str:
        return self.__str__()


class DerivedInductionVariable(InductionVariable):
    """
    Derived Induction Variable
    Represents j = c * i + d where identifier is the python id of the defining
    instruction for j.
    """

    def __init__(self, j_id, j, c, i, d, basic_block) -> None:
        self.j_id = j_id
        self.c = c
        self.d = d
        self.i = i
        self.j = j
        self.basic_block = basic_block

    def __str__(self) -> str:
        return f"{self.j} = {self.c} * {self.i} + {self.d} @{self.j_id}, {self.basic_block}"

    def __repr__(self) -> str:
        return self.__str__()


def find_basic_ivs(cfg, loop_blocks, var_invariant_map):
    """
    Find all instructions in loop_basic_block of cfg that satisfy
    the form
    i += e
    where i is defined exactly once in the loop and e is loop invariant

    var_invariant_map maps a variable to whether variable is loop ivnariant or not

    loop_blocks are all the blocks in the loop
    """
    basic_ivs = OrderedDict()
    for loop_basic_block in loop_blocks:
        for instr in cfg[loop_basic_block][INSTRS]:
            if is_add(instr):
                # check i defined only once in the loop
                defined_once = True
                for b in loop_blocks:
                    for b_instr in cfg[b][INSTRS]:
                        if DEST in b_instr and id(b_instr) != id(instr) and b_instr[DEST] == instr[DEST]:
                            defined_once = False
                if not defined_once:
                    continue

                # check i = i + e form
                def_var = instr[DEST]
                args = instr[ARGS]
                if def_var not in args:
                    continue

                # check e is loop invariant
                other_arg_invariant = False
                other_arg = None
                for a in args:
                    if a in var_invariant_map and var_invariant_map[a] == LOOP_INVARIANT:
                        other_arg_invariant = True
                        other_arg = a
                if not other_arg_invariant:
                    continue

                # to be restrictive about e, check it is a cosntant
                is_constant = False
                constant_instr = None
                for other_block in loop_blocks:
                    for other_instr in cfg[other_block][INSTRS]:
                        if DEST in other_instr and other_instr[DEST] == other_arg:
                            constant_instr = other_instr
                            is_constant = is_const(
                                constant_instr) and is_int(constant_instr)
                if not is_constant:
                    continue

                # add loop invariant instructions
                assert other_arg != None and constant_instr != None
                basic_ivs[def_var] = BasicInductionVariable(
                    id(instr), def_var, other_arg, constant_instr[VALUE], loop_basic_block)

    return basic_ivs


def find_derived_ivs(cfg, loop_blocks, var_invariant_map, basic_variable_map):
    """
    Find defintions like j = c * i + d
    where i is a basic indution variable and c, d are loop invariant

    We look for definitions j = a + d where d itself is loop invariant
    and a is c * i, c is loop invariant, i is basic.
    """
    derived_ivs = OrderedDict()
    mul_invariant_map = OrderedDict()
    const_map = OrderedDict()

    has_changed = True
    while has_changed:
        old_derived_ivs = deepcopy(derived_ivs)
        old_mul_invariant_map = deepcopy(mul_invariant_map)
        old_const_map = deepcopy(const_map)

        for loop_basic_block in loop_blocks:
            for instr in cfg[loop_basic_block][INSTRS]:
                instr_id = id(instr)
                if is_mul(instr):
                    def_var = instr[DEST]
                    # check only 1 defintion of this variable in the loop
                    has_one_def = True
                    for other_block in loop_blocks:
                        for other_instr in cfg[other_block][INSTRS]:
                            if DEST in other_instr and id(other_instr) != instr_id and other_instr[DEST] == def_var:
                                has_one_def = False

                    if has_one_def:
                        left = instr[ARGS][0]
                        right = instr[ARGS][1]
                        if left in basic_variable_map and right in var_invariant_map:
                            mul_inv = MulInvariant(
                                instr_id, def_var, right, left)
                            mul_invariant_map[def_var] = mul_inv
                        elif right in basic_variable_map and left in var_invariant_map:
                            mul_inv = MulInvariant(
                                instr_id, def_var, left, right)
                            mul_invariant_map[def_var] = mul_inv

                elif is_const(instr):
                    def_var = instr[DEST]
                    # check only 1 defintion of this variable in the loop
                    has_one_def = True
                    for other_block in loop_blocks:
                        for other_instr in cfg[other_block][INSTRS]:
                            if DEST in other_instr and id(other_instr) != instr_id and other_instr[DEST] == def_var:
                                has_one_def = False

                    if has_one_def and instr[TYPE] == INT:
                        val = instr[VALUE]
                        const_map[def_var] = val

                elif is_add(instr):
                    def_var = instr[DEST]
                    # check only 1 defintion of this variable in the loop
                    has_one_def = True
                    for other_block in loop_blocks:
                        for other_instr in cfg[other_block][INSTRS]:
                            if DEST in other_instr and id(other_instr) != instr_id and other_instr[DEST] == def_var:
                                has_one_def = False

                    if has_one_def:
                        left = instr[ARGS][0]
                        right = instr[ARGS][1]
                        if left in mul_invariant_map and right in const_map:
                            derived_inv = DerivedInductionVariable(
                                instr_id, def_var, mul_invariant_map[left].c, mul_invariant_map[left].i, right, loop_basic_block)
                            derived_ivs[def_var] = derived_inv
                        elif right in mul_invariant_map and left in const_map:
                            derived_inv = DerivedInductionVariable(
                                instr_id, def_var, mul_invariant_map[right].c, mul_invariant_map[right].i, left, loop_basic_block)
                            derived_ivs[def_var] = derived_inv

        has_changed = old_derived_ivs == derived_ivs and old_mul_invariant_map == mul_invariant_map and old_const_map == const_map

    return derived_ivs, const_map


def replace_ivs(cfg, dom, derived_ivs, basic_ivs, const_map, loop_preheader):
    """
    Replaces Induction Variables by changing j's update in the loop after i
    as well as the initialization of j in the preheader
    """
    for _, derived_iv in derived_ivs.items():
        assert type(derived_iv) == DerivedInductionVariable

        # insert initialization of j in the preheader
        j = derived_iv.j
        i = derived_iv.i
        c = derived_iv.c
        d = derived_iv.d
        e = basic_ivs[i]
        e_val = e.e_val

        # we must have a definite domination relation between j's bb and i's bb
        j_bb = derived_iv.basic_block
        j_id = derived_iv.j_id
        i_bb = e.basic_block
        i_id = e.i_id
        i_j_domination_relation = None
        if i_bb == j_bb:
            i_idx = None
            j_idx = None
            for i, instr in enumerate(cfg[i_bb][INSTRS]):
                if id(instr) == i_id:
                    i_idx = i
                elif id(instr) == j_id:
                    j_idx = i
            assert i_idx != None and j_idx != None
            assert i_idx != j_idx
            i_j_domination_relation = AFTER_I if i_idx < j_idx else BEFORE_I
        elif j_bb in dom[i_bb]:
            i_j_domination_relation = AFTER_I
        elif i_bb in dom[j_bb]:
            i_j_domination_relation = BEFORE_I

        # cannot figure out what relation j and i have, bail out
        if i_j_domination_relation == None:
            continue

        # insert initializer into preheader
        j_init_instr1 = {DEST: j, TYPE: INT, OP: CONST, VALUE: const_map[d]}
        insert_into_bb(cfg, loop_preheader, j_init_instr1)

        # insert update of j in the loop
        update_var1 = gen_new_var()
        update_var2 = gen_new_var()
        j_update_instr1 = {DEST: update_var1,
                           TYPE: INT, OP: CONST, VALUE: e_val}
        j_update_instr2 = {DEST: update_var2,
                           TYPE: INT, OP: MUL, ARGS: [c, update_var1]}
        j_update_instr3 = {DEST: j, TYPE: INT,
                           OP: ADD, ARGS: [j, update_var2]}
        # split into cases on where to insert instructions
        if i_j_domination_relation == AFTER_I:
            bb_instrs = cfg[j_bb][INSTRS]
            new_instrs = []
            for instr in bb_instrs:
                if id(instr) == j_id:
                    # do not add back original instr, as a deletion of j's update
                    new_instrs.append(j_update_instr1)
                    new_instrs.append(j_update_instr2)
                    new_instrs.append(j_update_instr3)
                else:
                    new_instrs.append(instr)
            cfg[j_bb][INSTRS] = new_instrs
        elif i_j_domination_relation == BEFORE_I:
            # delete old j update
            bb_instrs = cfg[j_bb][INSTRS]
            new_instrs = []
            for instr in bb_instrs:
                if id(instr) == j_id:
                    pass
                else:
                    new_instrs.append(instr)
            cfg[j_bb][INSTRS] = new_instrs
            # insert after i updates
            bb_instrs = cfg[i_bb][INSTRS]
            new_instrs = []
            for instr in bb_instrs:
                if id(instr) == i_id:
                    new_instrs.append(instr)
                    new_instrs.append(j_update_instr1)
                    new_instrs.append(j_update_instr2)
                    new_instrs.append(j_update_instr3)
                else:
                    new_instrs.append(instr)
            cfg[i_bb][INSTRS] = new_instrs
        else:
            raise RuntimeError(
                f"Cannot handle i_j_domination_relation {i_j_domination_relation}.")


def loop_induction_variables(func_args, cfg, dom, reaching_definitions, natural_loop, preheadermap):
    """
    Calculate and move induction variables for a single loop corresponding to natural loop
    """
    (natural_loop_blocks, _, natural_loop_header, _) = natural_loop
    loop_instrs = []
    for block in natural_loop_blocks:
        for instr in cfg[block][INSTRS]:
            loop_instrs.append((instr, block))
    _, var_invariant_map = identify_loop_invariant_instrs(
        cfg, func_args, natural_loop_blocks, loop_instrs, natural_loop_header, reaching_definitions)
    basic_ivs = find_basic_ivs(cfg, natural_loop_blocks, var_invariant_map)
    derived_ivs, const_map = find_derived_ivs(
        cfg, natural_loop_blocks, var_invariant_map, basic_ivs)
    replace_ivs(cfg, dom, derived_ivs, basic_ivs, const_map,
                preheadermap[natural_loop_header])


def func_induction_variables(func):
    """
    Calculate and move induction variables for a single function
    """
    natural_loops = get_natural_loops(func)

    # grab args
    func_args = []
    if ARGS in func:
        for a in func[ARGS]:
            func_args.append(a[NAME])

    # add preheaders to loops in func
    old_cfg = form_cfg_w_blocks(func)
    instrs_w_blocks = []
    for block in old_cfg:
        for instr in old_cfg[block][INSTRS]:
            instrs_w_blocks.append((instr, block))
    preheadermap, new_instrs = insert_preheaders(
        natural_loops, instrs_w_blocks)
    func[INSTRS] = new_instrs
    cfg = form_cfg_w_blocks(func)

    reaching_definitions = reaching_defs_func(func)
    dom, _ = get_dominators_w_cfg(cfg, list(cfg.keys())[0])

    for natural_loop in natural_loops:
        loop_induction_variables(
            func_args, cfg, dom, reaching_definitions, natural_loop, preheadermap)

    return join_cfg(cfg)


def induction_variables(prog):
    """
    Apply Induction Variable Elimination to a Program
    """
    for func in prog[FUNCTIONS]:
        new_instrs = func_induction_variables(func)
        func[INSTRS] = new_instrs
    return prog


@click.command()
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
@click.option('--ive', default=False, help='Run Induction Variable Elimination Original Program.')
def main(pretty_print, ive):
    prog = json.load(sys.stdin)
    if pretty_print == 'True':
        print(json.dumps(prog, indent=4, sort_keys=True))
    if ive == 'True':
        final_prog = induction_variables(prog)
    else:
        final_prog = prog
    if pretty_print == 'True':
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
