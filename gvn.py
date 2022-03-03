"""
Global Value Numbering

Implementation of Dominator Based Value Numbering from 
https://www.cs.tufts.edu/~nr/cs257/archive/keith-cooper/value-numbering.pdf
"""

import sys
import json
import click
from copy import deepcopy  # deepcopy used to create the "scoped" hash table

from ssa import is_ssa, bril_to_ssa
from cfg import form_cfg_w_blocks, join_cfg, INSTRS, SUCCS
from dominator_utilities import build_dominance_tree
from bril_core_constants import *
from bril_core_utilities import reverse_postorder_traversal, is_phi, is_unop, is_binop, is_const, is_id


def instr_to_expr(instr):
    if is_const(instr):
        return (instr[OP], instr[VALUE], instr[TYPE])
    elif is_id(instr) or is_unop(instr) or is_binop(instr) or is_phi(instr):
        return (instr[OP], *instr[ARGS])
    raise RuntimeError(
        f"Cannot Translate Instruction {instr} to a Value Numbering Expression.")


def expr_to_instr(dst, expr):
    assert type(expr) == tuple
    assert type(dst) == str
    assert len(expr) >= 2

    op = expr[0]
    if op not in BRIL_UNOPS + BRIL_BINOPS + [CONST, ID]:
        raise RuntimeError(
            f"Cannot Translate Expression {expr} to a Bril Instruction as {op} is not a unary nor binary operator.")
    if op == CONST:
        return {
            DEST: dst,
            OP: op,
            TYPE: BOOL if type(expr[1]) == bool else INT,
            VALUE: expr[1],
        }
    if op == ID:
        return {
            DEST: dst,
            TYPE: expr[2],
            OP: op,
            ARGS: expr[1],
        }
    return {
        DEST: dst,
        TYPE: OP_TO_TYPE[op],
        OP: op,
        ARGS: expr[1:],
    }


def canonocalize_expr(expr):
    assert type(expr) == tuple
    assert len(expr) >= 2

    op = expr[0]
    if op in BRIL_COMMUTE_BINOPS:

        return (op, *sorted(list(expr[1:])))
    return expr


def simplify_expr(expr):
    # TODO simplification, with interpretation
    assert type(expr) == tuple
    canonical = canonocalize_expr(expr)
    return canonical


def meaningless(instr):
    assert is_phi(instr)
    args = instr[ARGS]
    if args == []:
        raise RuntimeError(f"Phi node {instr} requires 1 or more arguments.")
    first_arg = args[0]
    all_same = True
    for arg in args:
        if arg != first_arg:
            all_same = False
            first_arg = None
            break
    return all_same, first_arg


def redundant(instr, phi2value_num):
    expr = simplify_expr(instr_to_expr(instr))
    if expr in phi2value_num:
        return True, phi2value_num[expr]
    return False, None


def dvnt(block, cfg, dominator_tree, var2value_num, expr2value_num):
    instrs = cfg[block][INSTRS]

    # create local phi to value num hash table
    phi2value_num = dict()
    # check phi instructions
    # ASSUMES all phi instructions are at beginning of basic block
    # otherwise order is messed up
    phi_instructions = []
    for instr in instrs:
        if is_phi(instr):
            fully_analyzed = True
            for a in instr[ARGS]:
                if a not in var2value_num:
                    fully_analyzed = False
                    break
            # not all components of phi function have value number assigned
            dst = instr[DEST]
            no_meaning, meaning_var = meaningless(instr)
            is_redundant, redundant_var = redundant(instr, phi2value_num)
            if not fully_analyzed:
                var2value_num[dst] = dst
                phi2value_num[instr_to_expr(instr)] = dst
                # add instruction
                phi_instructions.append(instr)
            elif no_meaning:
                assert type(meaning_var) == str
                var2value_num[dst] = meaning_var
            elif is_redundant:
                assert type(redundant_var) == str
                var2value_num[dst] = redundant_var
            # phi function is not meaningless not redundant
            else:
                var2value_num[dst] = dst
                phi2value_num[instr_to_expr(instr)] = dst
                # add instruction
                phi_instructions.append(instr)
        else:
            phi_instructions.append(instr)

    # check all regular instructions
    gvn_instructions = []
    for instr in phi_instructions:
        if is_id(instr) or is_const(instr) or is_binop(instr) or is_unop(instr):
            # overwrite args with value number args
            if not is_const(instr):
                args = instr[ARGS]
                new_args = [var2value_num[arg] for arg in args]
                instr[ARGS] = new_args

            # get canonical expression
            expr = instr_to_expr(instr)
            new_expr = simplify_expr(expr)
            dst = instr[DEST]
            if new_expr != expr:
                expr = new_expr
                instr = expr_to_instr(dst, expr)

            if expr in expr2value_num:
                # get canonical location (SSA name)
                value_num = expr2value_num[expr]
                # set the cloud
                var2value_num[dst] = value_num
                # we do not add this instruction as it is a repeat
            else:
                # set the cloud
                var2value_num[dst] = dst
                # set new canonical location (SSA name)
                expr2value_num[expr] = dst
                # we add this instruction
                gvn_instructions.append(instr)
        elif is_phi(instr):
            gvn_instructions.append(instr)
        else:
            # replace all args with value numbering variable names
            if ARGS in instr:
                args = instr[ARGS]
                new_args = [var2value_num[arg] for arg in args]
                instr[ARGS] = new_args
            # don't bother changing destination, if it exists, as it
            # could be a call, and calls can have side effects

            # add instr
            gvn_instructions.append(instr)

    cfg[block][INSTRS] = gvn_instructions

    # adjust phi nodes of successors
    for s in cfg[block][SUCCS]:
        for s_instr in cfg[s][INSTRS]:
            if is_phi(s_instr):
                new_args = []
                for a in s_instr[ARGS]:
                    if a in var2value_num:
                        new_args.append(var2value_num[a])
                    else:
                        new_args.append(a)
                s_instr[ARGS] = new_args

    # grab reverse post order
    reverse_sub_children = reverse_postorder_traversal(block, dominator_tree)
    actual_children = dominator_tree[block]
    reverse_children = []
    for r in reverse_sub_children:
        if r in actual_children:
            reverse_children.append(r)

    # traverse children of dominator tree in reverse post order
    for c in dominator_tree[block]:
        # deepcopy to create scoping
        dvnt(c, cfg, dominator_tree, var2value_num, deepcopy(expr2value_num))


def gvn_func(func):
    cfg = form_cfg_w_blocks(func)
    dominator_tree, _ = build_dominance_tree(func)
    header = list(cfg.keys())[0]

    var2value_num = dict()
    expr2value_num = dict()
    # handle functions with arguments
    if ARGS in func:
        for arg in func[ARGS]:
            name = arg[NAME]
            var2value_num[name] = name
            expr2value_num[(ARGUMENT, name)] = name

    dvnt(header, cfg, dominator_tree, var2value_num, expr2value_num)

    return join_cfg(cfg)


def gvn_main(program):
    # enters as SSA/Or Transform as needed
    try:
        is_ssa(program)
    except:
        program = bril_to_ssa(program)

    # GVN on functions
    for func in program["functions"]:
        new_instrs = gvn_func(func)
        func["instrs"] = new_instrs

    # exit as SSA
    is_ssa(program)
    return program


@click.command()
@click.option('--gvn', default=False, help='Runs Global Value Numbering on SSA Form Program.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After GVN.')
def main(gvn, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if gvn:
        final_prog = gvn_main(prog)
    else:
        final_prog = prog
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
