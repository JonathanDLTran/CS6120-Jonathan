import sys
import json
import click
from collections import OrderedDict
from copy import deepcopy

from cfg import form_cfg_succs_preds, PREDS, SUCCS


def big_intersection(lst):
    assert type(lst) == list
    if lst == []:
        return set()
    out = lst[0]
    assert type(out) == set
    for e in lst:
        out = out.intersection(e)
    return out


def dfs(cfg, current, visited):
    """
    Finds all reachable vertices in cfg, from current vertex
    start vertex must be in cfg
    """
    assert type(visited) == set
    assert current in cfg

    visited.add(current)
    for n in cfg[current][SUCCS]:
        if n not in visited:
            result = dfs(cfg, n, visited)
            visited = visited.union(result)
    return visited


def get_dominators(func):
    """
    Calculates Dominators for a function

    Gives the dominators as a dictionary, e.g. BasicBlock::[Dominators of BasicBlock]
    """
    assert type(func) == dict
    func_instructions = func["instrs"]
    cfg = form_cfg_succs_preds(func_instructions)

    # set up before iteration
    # NOTE: I am not sure if this is completely correct, but it *SEEMS* to handle
    # unreachable blocks. Otherwise, some SCC algorithm is probably needed
    dom = OrderedDict()
    reachable_blocks = set()
    if len(cfg) >= 1:
        reachable_blocks = dfs(cfg, list(cfg.keys())[0], set())
    for bb_name in cfg:
        if bb_name in reachable_blocks:
            dom[bb_name] = reachable_blocks
        else:
            dom[bb_name] = set()

    # iterate to convergence
    dom_changed = True
    while dom_changed:
        old_dom = deepcopy(dom)

        for bb_name in cfg:
            dom_predecessors = [dom[p] for p in cfg[bb_name][PREDS]]
            intersection = big_intersection(dom_predecessors)
            dom[bb_name] = {bb_name}.union(intersection)

        dom_changed = old_dom != dom

    return dom


def dominators(prog):
    for func in prog["functions"]:
        dom = get_dominators(func)
        for bb_name, dominated in dom.items():
            print(f"\t{bb_name}:\t[{', '.join(dominated)}]")


def build_dominance_tree(func):
    pass


def build_dominance_frontier(func):
    pass


@click.command()
@click.option('--dominator', default=False, help='Print Dominators.')
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(dominator, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if dominator:
        dominators(prog)


if __name__ == "__main__":
    main()
