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
    out = OrderedDict()
    for i, (name, block) in enumerate(name2block.items()):
        last = block[-1]
        if last['op'] == ['jmp', 'br']:
            succ = last['labels']
        elif last['op'] == 'ret':
            succ = []
        else:
            if i == len(name2block) - 1:
                succ = []
            else:
                succ = list(name2block.keys())[i + 1]
        out[name] = succ
    return out


def mycfg():
    prog = json.load(sys.stdin)
    for func in prog["functions"]:
        name2block = block_map(form_blocks(func['instrs']))
        print(name2block)
        cfg = get_cfg(name2block)
        print(cfg)


if __name__ == "__main__":
    mycfg()