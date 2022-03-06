from copy import deepcopy
import click
import sys
import json

from cfg import form_blocks, join_blocks


def mark_sweep_dce(program):
    """
    Implementation of Mark Sweep Style DCE to remove more dead code. Meant to 
    work in conjunction with SSA code.

    Can be run alongside other passes with lvn/gvn.
    """
    pass


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


def dce(program, global_delete, local_delete):
    """
    Naive DCE wrapper method
    """
    if global_delete == None and local_delete == None:
        return iterate_dce(iterate_dce(program, local_dce), delete_unused_dce)
    elif global_delete == None and local_delete:
        return iterate_dce(program, local_dce)
    elif global_delete and local_delete == None:
        return iterate_dce(program, delete_unused_dce)
    return iterate_dce(iterate_dce(program, local_dce), delete_unused_dce)


@click.command()
@click.option('--global-delete', default=1, help='Delete Globally.')
@click.option('--local-delete', default=1, help='Delete Locally.')
@click.option('--pretty-print', default=False, help='Pretty Print Before and After Optimization.')
def main(global_delete, local_delete, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    final_prog = dce(prog, global_delete, local_delete)
    if pretty_print:
        print(json.dumps(final_prog, indent=4, sort_keys=True))
    print(json.dumps(final_prog))


if __name__ == "__main__":
    main()
