import graphviz


import random_cfg


def build_dot_cfg(cfg):
    assert type(cfg) == tuple
    assert len(cfg) == 2
    _, nodes = cfg

    dot = graphviz.Digraph(comment='CFG')
    for node in nodes:
        name = str(node.get_name())
        dot.node(name, name if name != '0' else "Entry")

    for node in nodes:
        name = str(node.get_name())
        neighbors = node.get_neighbors()
        for neighbor in neighbors:
            neighbor_name = str(neighbor.get_name())
            dot.edge(name, neighbor_name, constraint='false')

    dot.render('./cfg').replace('\\', '/')


def main():
    build_dot_cfg(random_cfg.gen_cfg(10))


if __name__ == "__main__":
    main()
