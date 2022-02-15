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
            print(f"\t{bb_name}:\t[{', '.join(sorted(dominated))}]")


def get_strict_dominators(dom):
    """
    Get strict dominators, e.g. dominators of a node n, excluding n itself
    """
    strict_dom = OrderedDict()
    for bb_name, doms in dom.items():
        new_doms = deepcopy(doms)
        new_doms.remove(bb_name)
        strict_dom[bb_name] = new_doms
    return strict_dom


def get_immediate_dominators(strict_dom):
    """
    For a vertex v, get the unique vertex u that strictly dominates v,
    but that u does not strictly dominate any other vertex u' that also 
    strictly dominates v.

    If there is no such vertex, then the vertex is the entry vertex,
    and it is immediately dominated by itself,

    (Kinda like a LUB for strict dominators)
    """
    imm_dom = OrderedDict()
    for node1, strict_lst in strict_dom.items():
        immediate = []
        for node2 in strict_lst:
            can_add = True
            for node3 in strict_lst:
                if node2 != node3:
                    node3_strict = strict_dom[node3]
                    if node2 in node3_strict:
                        can_add = False
                        break
            if can_add:
                immediate.append(node2)
                break
        if immediate != []:
            assert len(immediate) == 1
            imm_dom[node1] = immediate[0]
        else:
            # special case: entry immediately dominates itself
            imm_dom[node1] = node1
    return imm_dom


def build_dominance_tree(func):
    dom = get_dominators(func)
    strict_dom = get_strict_dominators(dom)
    imm_dom = get_immediate_dominators(strict_dom)
    nodes = OrderedDict()
    tree = OrderedDict()
    for bb, dom_obj in imm_dom.items():
        nodes[bb] = None
        if bb != dom_obj:
            if dom_obj not in tree:
                tree[dom_obj] = [bb]
            else:
                tree[dom_obj].append(bb)
    return tree, nodes


def get_tree_graph(tree, func, nodes):
    print('digraph {} {{'.format(func['name']))
    for name in nodes:
        print('  {};'.format(name))
    for name, succs in tree.items():
        for succ in succs:
            print('  {} -> {};'.format(name, succ))
    print('}')


def dominance_tree(prog):
    for func in prog["functions"]:
        tree, nodes = build_dominance_tree(func)
        tree_str = get_tree_graph(tree, func, nodes)


def build_dominance_frontier(func):
    pass


@click.command()
@click.option('--dominator', default=False, help='Print Dominators.')
@click.option('--tree', default=False, help='Print Dominator Tree.')
@click.option('--frontier', default=False, help='Print Domination Frontier.')
@click.option('--pretty-print', default=False, help='Pretty Print Original Program.')
def main(dominator, tree, frontier, pretty_print):
    prog = json.load(sys.stdin)
    if pretty_print:
        print(json.dumps(prog, indent=4, sort_keys=True))
    if dominator:
        dominators(prog)
    if tree:
        dominance_tree(prog)
    if frontier:
        pass


if __name__ == "__main__":
    main()
