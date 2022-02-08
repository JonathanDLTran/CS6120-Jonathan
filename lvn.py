import click
from copy import deepcopy
import sys
import json

from scipy.fft import dst

from cfg import form_blocks, join_blocks
from bril_core_constants import *


LVN_NUMBER = 0
VARIABLE_NUMBER = 0


ARG_LVN_VALUE = "arg-value"


def gen_fresh_lvn_num():
    global LVN_NUMBER
    LVN_NUMBER += 1
    return LVN_NUMBER


def gen_fresh_variable(var):
    global VARIABLE_NUMBER
    VARIABLE_NUMBER += 1
    return f"{var}_{VARIABLE_NUMBER}"


def arg_to_lvn_value(arg, func_args, var_to_num):
    if arg in var_to_num:
        return var_to_num[arg]
    elif arg in func_args:
        return -1 * (func_args.index(arg) + 1)
    raise RuntimeError(
        f"LVN Pass: Variable {arg} was defined before its first use.")


def instr_to_lvn_value(instr, func_args, var_to_num):
    if OP in instr and instr[OP] == CONST:
        return (CONST, instr[VALUE])
    elif OP in instr and instr[OP] in BRIL_BINOPS + BRIL_UNOPS:
        return (instr[OP], *list(map(lambda a: arg_to_lvn_value(a, func_args, var_to_num), instr[ARGS])))
    elif OP in instr and instr[OP] in [CALL]:
        return (CALL, *list(map(lambda a: arg_to_lvn_value(a, func_args, var_to_num), instr[ARGS])))
    elif OP in instr and instr[OP] in [ID]:
        return (ID, *list(map(lambda a: arg_to_lvn_value(a, func_args, var_to_num), instr[ARGS])))
    raise RuntimeError(f"Requires Instruction to Assign to Variable\n{instr}.")


def get_canonical_loc(curr_lvn_num, num_value_loc):
    for (lvn_num, _, canonical_loc) in num_value_loc:
        if lvn_num == curr_lvn_num:
            return canonical_loc
    else:
        raise RuntimeError("LVN Num must be in num_value_loc table.")


def get_lvn_value(curr_lvn_num, num_value_loc):
    for (lvn_num, lvn_value, _) in num_value_loc:
        if lvn_num == curr_lvn_num:
            return lvn_value
    else:
        raise RuntimeError("LVN Num must be in num_value_loc table.")


def lvn_value_to_instr(dst, lvn_value, num_value_loc):
    assert type(lvn_value) == tuple
    assert len(lvn_value) >= 2

    first = lvn_value[0]
    if first == CONST:
        assert len(lvn_value) == 2
        return {DEST: dst, OP: CONST, TYPE: INT, VALUE: lvn_value[1]}
    elif first in [ADD, SUB, MUL, DIV]:
        assert len(lvn_value) == 3
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        arg2 = get_canonical_loc(lvn_value[2], num_value_loc)
        return {DEST: dst, OP: first, TYPE: INT, ARGS: [arg1, arg2]}
    elif first in [EQ, LT, GT, LE, GE, AND, OR]:
        assert len(lvn_value) == 3
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        arg2 = get_canonical_loc(lvn_value[2], num_value_loc)
        return {DEST: dst, OP: first, TYPE: BOOL, ARGS: [arg1, arg2]}
    elif first in [NOT]:
        assert len(lvn_value) == 2
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        return {DEST: dst, OP: NOT, TYPE: BOOL, ARGS: [arg1]}
    elif first in [CALL]:
        assert len(lvn_value) >= 2
        args = list(map(lambda a: get_canonical_loc(
            a, num_value_loc), lvn_value[1:]))
        return {DEST: dst, OP: CALL, ARGS: args}
    elif first in [ID]:
        assert len(lvn_value) == 2
        arg1 = get_canonical_loc(lvn_value[1], num_value_loc)
        return {DEST: dst, OP: ID, ARGS: [arg1]}
    else:
        raise RuntimeError(f"Unmatched LVN Value type {lvn_value}")


def instr_lvn(instr, remainder_bb, func_args, var_to_num, num_value_loc):
    if DEST in instr:
        dst_var = instr[DEST]
        new_lvn_val = instr_to_lvn_value(instr, func_args, var_to_num)

        # copy propagation shortcut
        if (new_lvn_val[0] == ID):
            assert len(new_lvn_val) == 2
            lvn_table_num = new_lvn_val[1]
            var_to_num[dst_var] = lvn_table_num
            arg = get_canonical_loc(lvn_table_num, num_value_loc)
            return {DEST: dst_var, OP: ID, TYPE: instr[TYPE], ARGS: [arg]}

        in_lvn_table = False
        in_lvn_table_num = None
        for (lvn_num, lvn_val, _) in num_value_loc:
            if lvn_val == new_lvn_val:
                in_lvn_table = True
                in_lvn_table_num = lvn_num
                break
        if in_lvn_table:
            assert in_lvn_table_num != None
            var_to_num[dst_var] = in_lvn_table_num
            return {DEST: dst_var, OP: ID, TYPE: instr[TYPE], ARGS: [get_canonical_loc(in_lvn_table_num, num_value_loc)]}
        else:
            new_lvn_num = gen_fresh_lvn_num()

            # consider that the variable will get rewritten
            dest_overwritten = False
            for instr in remainder_bb:
                if DEST in instr and instr[DEST] == dst_var:
                    dest_overwritten = True
                    break
            if dest_overwritten:
                new_dst_var = gen_fresh_variable(dst_var)
                row_triple = (new_lvn_num, new_lvn_val, new_dst_var)
                num_value_loc.append(row_triple)
                # keep mapping with old destination variable
                var_to_num[dst_var] = new_lvn_num
                # but replace instruction with new variable as that is the canonical location
                return lvn_value_to_instr(new_dst_var, new_lvn_val, num_value_loc)
            else:
                row_triple = (new_lvn_num, new_lvn_val, dst_var)
                num_value_loc.append(row_triple)
                var_to_num[dst_var] = new_lvn_num
                return lvn_value_to_instr(dst_var, new_lvn_val, num_value_loc)
    else:
        if ARGS in instr and LABELS not in instr:
            new_instr = deepcopy(instr)
            new_instr[ARGS] = list(map(lambda v: get_canonical_loc(
                var_to_num[v], num_value_loc), instr[ARGS]))
            return new_instr
        else:
            return instr


def lvn(program):
    # we ignore programs with branching due to variable definiton issues.
    for func in program["functions"]:
        for instr in func["instrs"]:
            if LABELS in instr:
                return program
    for func in program["functions"]:
        basic_blocks = form_blocks(func["instrs"])
        new_basic_blocks = []
        for bb in basic_blocks:
            new_bb = []
            var_to_num = {}
            num_value_loc = []
            func_args = []
            if ARGS in func:
                for arg in func[ARGS]:
                    func_args.append(arg)
            for i, instr in enumerate(bb):
                remainder_bb = bb[i + 1:]
                new_instr = instr_lvn(
                    instr, remainder_bb, func_args, var_to_num, num_value_loc)
                new_bb.append(new_instr)
            new_basic_blocks.append(new_bb)
        func["instrs"] = join_blocks(new_basic_blocks)
    return program


@click.command()
def main():
    prog = json.load(sys.stdin)
    print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = lvn(prog)
    print(json.dumps(final_prog, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
