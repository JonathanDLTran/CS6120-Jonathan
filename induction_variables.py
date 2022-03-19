"""
Implementation of Induction Variable Elimination for Loops 

ASSSUMED NOT TO BE IN SSA FORM
"""
import sys
import json
import click
from collections import OrderedDict

from reaching_definitions import reaching_defs_func
from licm import insert_preheaders, identify_loop_invariant_instrs, LOOP_INVARIANT
from cfg import form_cfg_w_blocks, join_cfg, INSTRS
from dominator_utilities import get_natural_loops
from bril_core_constants import *
from bril_core_utilities import is_add, is_mul


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

    def __init__(self, i_id, i, e) -> None:
        self.i_id = i_id
        self.i = i
        self.e = e

    def __str__(self) -> str:
        return f"{self.i} += {self.e} * {self.i} @{self.i_id}"

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

    def __init__(self, j_id, j, c, i, d) -> None:
        self.j_id = j_id
        self.c = c
        self.d = d
        self.i = i
        self.j = j

    def __str__(self) -> str:
        return f"{self.j} = {self.c} * {self.i} + {self.d} @{self.j_id}"

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

                # add loop invariant instructions
                assert other_arg != None
                basic_ivs[def_var] = BasicInductionVariable(
                    id(instr), def_var, other_arg)

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
                        mul_inv = MulInvariant(instr_id, def_var, right, left)
                        mul_invariant_map[def_var] = mul_inv
                    elif right in basic_variable_map and left in var_invariant_map:
                        mul_inv = MulInvariant(instr_id, def_var, left, right)
                        mul_invariant_map[def_var] = mul_inv

            elif is_add(instr):
                def_var = instr[DEST]
                left = instr[ARGS][0]
                right = instr[ARGS][1]
                if left in mul_invariant_map and right in var_invariant_map:
                    derived_inv = DerivedInductionVariable(
                        instr_id, def_var, left.c, left.i, right)
                    derived_ivs[def_var] = derived_inv
                elif right in mul_invariant_map and left in var_invariant_map:
                    derived_inv = DerivedInductionVariable(
                        instr_id, def_var, right.c, right.i, left)
                    derived_ivs[def_var] = derived_inv

    return derived_ivs


def replace_ivs(cfg, derived_ivs, preheadermap):
    """
    Replaces Induction Variables
    """
    pass


def loop_induction_variables(func_args, cfg, reaching_definitions, natural_loop, preheadermap):
    """
    Calculate and move induction variables for a single loop corresponding to natural loop
    """
    (natural_loop_blocks, _, natural_loop_header, _) = natural_loop
    _, var_invariant_map = identify_loop_invariant_instrs(
        cfg, func_args, natural_loop_blocks, natural_loop_header, reaching_definitions)
    basic_ivs = find_basic_ivs(cfg, natural_loop_blocks, var_invariant_map)
    derived_ivs = find_derived_ivs(
        cfg, natural_loop_blocks, var_invariant_map, basic_ivs)
    replace_ivs(cfg, derived_ivs, preheadermap)


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

    for natural_loop in natural_loops:
        loop_induction_variables(
            func_args, cfg, reaching_definitions, natural_loop, preheadermap)

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
