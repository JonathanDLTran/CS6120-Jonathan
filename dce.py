from copy import deepcopy
import click
import sys
import json

from cfg import form_blocks, join_blocks


def delete_unused_dce(program):
    """
    Delete all instructions for which a variable is assigned but never read from.
    """
    for func in program["functions"]:
        written_variables = set()
        for instr in func["instrs"]:
            if "dest" in instr:
                written_variables.add(instr["dest"])

        for instr in func["instrs"]:
            if "args" in instr:
                args = set(instr["args"])
                written_variables -= args

        new_instrs = []
        for instr in func["instrs"]:
            if "dest" in instr:
                if instr["dest"] not in written_variables:
                    new_instrs.append(instr)
            else:
                new_instrs.append(instr)

        func["instrs"] = new_instrs

    return program


def local_dce(program):
    """
    Eliminate instructions that are written over without being read, inside a 
    basic block.
    """
    for func in program["functions"]:
        basic_blocks = form_blocks(func["instrs"])
        new_basic_blocks = []
        for bb in basic_blocks:
            new_bb = []
            to_delete = []
            last_use = dict()
            for idx, instr in enumerate(bb):
                if "args" in instr:
                    args = instr["args"]
                    for a in args:
                        if a in last_use:
                            (def_idx, _) = last_use[a]
                            last_use[a] = (def_idx, idx)
                if "dest" in instr:
                    dst = instr["dest"]
                    if dst in last_use:
                        (def_idx, use) = last_use[dst]
                        if use == None:
                            to_delete.append(def_idx)
                    last_use[dst] = (idx, None)

            # This is in fact incorrect! A value in one bb not used can still be used later
            # as in the diamond patter. I leave it commented out as a lesson for myself.
            # for dst, (def_idx, last_use_idx) in last_use.items():
            #     if last_use_idx == None:
            #         to_delete.append(def_idx)

            for idx, instr in enumerate(bb):
                if idx not in to_delete:
                    new_bb.append(instr)

            new_basic_blocks.append(new_bb)
        func["instrs"] = join_blocks(new_basic_blocks)
    return program


def iterate_dce(program, dce_method):
    """
    Iterates specified DCE method
    """
    has_changed = True
    while has_changed:
        old_program = deepcopy(program)
        program = dce_method(program)
        has_changed = not (program == old_program)

    return program


def dce(program):
    """
    Naive DCE wrapper method
    """
    return iterate_dce(program, local_dce)


# @click.command()
# @click.option('--del-unused', default=1, help='Delete Unused.')
# @click.option('--del-unused-iterate', help='Delete Unused with Iteration.')
def main():
    prog = json.load(sys.stdin)
    print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = dce(prog)
    print(json.dumps(final_prog, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()
