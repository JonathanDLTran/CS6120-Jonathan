import click
import random

MAX_NODES = 10


class CFGNode(object):
    node_number = 0

    def __init__(self):
        self.name = CFGNode.node_number
        self.neighbors = []
        self.instrs = []
        CFGNode.node_number += 1

    def get_neighbors(self):
        return self.neighbors

    def set_neighbors(self, neighbors):
        self.neighbors = neighbors

    def get_name(self):
        return self.name

    def get_instrs(self):
        return self.instrs

    def set_instrs(self, instrs):
        self.instrs = instrs

    def __str__(self) -> str:
        stringified_neighbors = ', '.join(
            list(map(lambda node: str(node.get_name()), self.neighbors)))
        return f"This is node {self.name} and it has neighbors [{stringified_neighbors}]."

    def __repr__(self) -> str:
        return self.__str__()


def gen_cfg(num_nodes):
    assert type(num_nodes) == int
    assert 0 < num_nodes

    # create nodes
    entry_node = CFGNode()
    nodes_list = [entry_node]

    for _ in range(num_nodes - 1):
        new_node = CFGNode()
        nodes_list.append(new_node)
    assert len(nodes_list) == num_nodes

    # add edges
    for node in nodes_list:
        num_neighbors = random.randint(0, len(nodes_list))
        new_neighbors = random.sample(nodes_list, num_neighbors)
        node.set_neighbors(new_neighbors)

    return (entry_node, nodes_list)


@click.command()
@click.option("--nodes", default=MAX_NODES, help="Number of CFG nodes.")
def main(nodes):
    _, new_nodes = gen_cfg(nodes)
    print(new_nodes)


if __name__ == "__main__":
    main()
