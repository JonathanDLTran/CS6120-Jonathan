from email.policy import strict
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
    domby = OrderedDict()
    reachable_blocks = set()
    if len(cfg) >= 1:
        reachable_blocks = dfs(cfg, list(cfg.keys())[0], set())
    for bb_name in cfg:
        if bb_name in reachable_blocks:
            domby[bb_name] = reachable_blocks
        else:
            domby[bb_name] = set()

    # iterate to convergence
    dom_changed = True
    while dom_changed:
        old_dom = deepcopy(domby)

        for bb_name in cfg:
            dom_predecessors = [domby[p] for p in cfg[bb_name][PREDS]]
            intersection = big_intersection(dom_predecessors)
            domby[bb_name] = {bb_name}.union(intersection)

        dom_changed = old_dom != domby

    dom = OrderedDict()
    for bb in cfg:
        dominates = set()
        for otherbb, dominatedby in domby.items():
            if bb in dominatedby:
                dominates.add(otherbb)
        dom[bb] = list(dominates)

    return dom, domby


def dominators(prog):
    for func in prog["functions"]:
        _, domby = get_dominators(func)
        # for bb_name, dominates in dom.items():
        #     print(f"\t{bb_name} dominates:\t[{', '.join(sorted(dominates))}]")
        for bb_name, dominated in domby.items():
            print(
                f"\t{bb_name} is dominated by:\t[{', '.join(sorted(dominated))}]")


def get_strict_dominators(dom):
    """
    Get strict dominators, e.g. dominators of a node n, excluding n itself
    """
    strict_dom = OrderedDict()
    for bb_name, doms in dom.items():
        new_doms = deepcopy(doms)
        new_doms = set(new_doms).difference({bb_name})
        strict_dom[bb_name] = list(new_doms)
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
    _, domby = get_dominators(func)
    strict_dom = get_strict_dominators(domby)
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
            if bb not in tree:
                tree[bb] = []
        else:
            # entry point:
            tree[bb] = []
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
        get_tree_graph(tree, func, nodes)


def build_dominance_frontier(func):
    """
    The dominator frontier is a set of nodes defined for every node (basic block)
    Consider a basic block A. The dominance frontier of A contains a node B
    iff A does not strictly dominate B but A dominiates some predecessor of B.
    """
    func_instructions = func["instrs"]
    cfg = form_cfg_succs_preds(func_instructions)
    dom, _ = get_dominators(func)
    strict_dom = get_strict_dominators(dom)
    out = OrderedDict()
    for nodeA in cfg:
        nodeA_dominance_frontier = set()
        for nodeB in cfg:
            if nodeB not in strict_dom[nodeA]:
                for nodeC in cfg[nodeB][PREDS]:
                    if nodeC in dom[nodeA]:
                        nodeA_dominance_frontier.add(nodeB)
                        break
        out[nodeA] = list(nodeA_dominance_frontier)
    return out


def dominance_frontier(prog):
    for func in prog["functions"]:
        frontier = build_dominance_frontier(func)
        for bb_name, dominated in frontier.items():
            print(f"\t{bb_name}:\t[{', '.join(sorted(dominated))}]")


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
        print("Dominators")
        dominators(prog)
    if tree:
        print("Dominator Tree")
        dominance_tree(prog)
    if frontier:
        print("Dominance Frontier")
        dominance_frontier(prog)


if __name__ == "__main__":
    main()
