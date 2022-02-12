import json
import sys
from collections import OrderedDict

TERMINATORS = ["jmp", "br", "ret"]


def form_blocks(body):
    cur_block = []
    for instr in body:
        if "op" in instr:
            cur_block.append(instr)
            if instr["op"] in TERMINATORS:
                yield cur_block
                cur_block = []
        else:
            yield cur_block
            cur_block = [instr]
    yield cur_block


def join_blocks(blocks):
    new_instrs = []
    for bb in blocks:
        for instr in bb:
            new_instrs.append(instr)
    return new_instrs


def block_map(blocks):
    out = OrderedDict()

    for i, block in enumerate(blocks):
        if 'label' in block[0]:
            name = block[0]['label']
            block = block[1:]
        else:
            name = f'b{i}'
        out[name] = block

    return out


def get_cfg(name2block):
    out = {}
    for i, (name, block) in enumerate(name2block.items()):
        last = block[-1]
        if last['op'] in ['jmp', 'br']:
            succ = last['labels']
        elif last['op'] == 'ret':
            succ = []
        else:
            if i == len(name2block) - 1:
                succ = []
            else:
                succ = [list(name2block.keys())[i + 1]]
        out[name] = succ
    return out


def get_graphviz(func, cfg, name2block):
    print('digraph {} {{'.format(func['name']))
    for name in name2block:
        print('  {};'.format(name))
    for name, succs in cfg.items():
        for succ in succs:
            print('  {} -> {};'.format(name, succ))
    print('}')


def main():
    prog = json.load(sys.stdin)
    for func in prog["functions"]:
        name2block = block_map(form_blocks(func['instrs']))
        cfg = get_cfg(name2block)
        get_graphviz(func, cfg, name2block)


if __name__ == "__main__":
    main()
