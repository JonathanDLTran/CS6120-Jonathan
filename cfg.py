import json
import sys
from collections import OrderedDict

TERMINATORS = ["jmp", "br", "ret"]

PREDS = "preds"
SUCCS = "succs"


def form_cfg_succs_preds(body):
    """
    Takes a Function Body and turns it into a CFG
    representation with Successors and Predecessors with Multiple Basic Blocks
    """
    assert type(body) == list
    blocks = form_blocks(body)
    name2block = form_block_dict(blocks)
    succs_cfg = get_cfg(name2block)
    preds_cfg = OrderedDict()
    for bb_name in succs_cfg:
        preds = []
        for bb_name1, succs in succs_cfg.items():
            if bb_name in succs:
                preds.append(bb_name1)
        preds_cfg[bb_name] = preds

    out = OrderedDict()
    for bb_name in succs_cfg:
        out[bb_name] = {PREDS: preds_cfg[bb_name], SUCCS: succs_cfg[bb_name]}
    return out


def form_blocks(body):
    cur_block = []
    for instr in body:
        if "op" in instr:
            cur_block.append(instr)
            if instr["op"] in TERMINATORS:
                yield cur_block
                cur_block = []
        else:
            if cur_block:
                yield cur_block
            cur_block = [instr]
    if cur_block:
        yield cur_block


def join_blocks(blocks):
    """
    Joins a list of basic blocks into 1 function body
    Inverts form_blocks
    """
    new_instrs = []
    for bb in blocks:
        for instr in bb:
            new_instrs.append(instr)
    return new_instrs


def block_map(blocks):
    """
    Converts a list of basic blocks into a map of label to the instructions in block
    """
    out = OrderedDict()

    for i, block in enumerate(blocks):
        if 'label' in block[0]:
            name = block[0]['label']
            block = block[1:]
        else:
            name = f'b{i}'
        out[name] = block

    return out


def form_block_dict(blocks):
    """
    Similar to Block Map: But retain labels in instructions
    Internally Preserves labels, unlike Block Map, which tries to remove labels
    and use them solely as dictionary keys.
    """
    out = OrderedDict()

    for i, block in enumerate(blocks):
        if 'label' in block[0]:
            name = block[0]['label']
        else:
            name = f'b{i}'
        out[name] = block

    return out


def get_cfg(name2block):
    """
    Converts Name2Block into a Successor Labeled CFG
    """
    out = OrderedDict()
    for i, (name, block) in enumerate(name2block.items()):
        if block != []:
            last = block[-1]
            if 'op' in last and last['op'] in ['jmp', 'br']:
                succ = last['labels']
            elif 'op' in last and last['op'] == 'ret':
                succ = []
            else:
                if i == len(name2block) - 1:
                    succ = []
                else:
                    succ = [list(name2block.keys())[i + 1]]
            out[name] = succ
        else:
            if i == len(name2block) - 1:
                succ = []
            else:
                succ = [list(name2block.keys())[i + 1]]
            out[name] = succ
    return out


def form_cfg(func):
    """
    Takes a Function Body and turns it into a CFG, labeled with successors only 
    (predecessors not included)
    """
    return get_cfg(block_map(form_blocks(func['instrs'])))


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
