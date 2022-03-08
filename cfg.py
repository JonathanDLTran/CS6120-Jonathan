import json
import sys
from collections import OrderedDict

from bril_core_constants import *

TERMINATORS = ["jmp", "br", "ret"]

PREDS = "preds"
SUCCS = "succs"
INSTRS = "instrs"


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


def join_blocks_w_labels(block_dict):
    """
    Joins a dictionary of basic blocks into 1 function body
    Inverts form_blocks, But adds label if label instr was not there previously
    """
    new_instrs = []
    for label, bb in block_dict.items():
        if len(bb) != 0 and 'label' not in bb[0]:
            new_instrs.append({'label': label})
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


def get_cfg_w_blocks(name2block):
    """
    Converts Name2Block into a Successor, Predecessor Labeled CFG,
    WITH BLOCKS of Instructions
    """
    succs_cfg = OrderedDict()
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
            result = {INSTRS: block, SUCCS: succ, PREDS: []}
            succs_cfg[name] = result
        else:
            if i == len(name2block) - 1:
                succ = []
            else:
                succ = [list(name2block.keys())[i + 1]]
            result = {INSTRS: block, SUCCS: succ, PREDS: []}
            succs_cfg[name] = result

    preds_cfg = OrderedDict()
    for bb_name in succs_cfg:
        preds = []
        for bb_name_pred, triple_dict in succs_cfg.items():
            if bb_name in triple_dict[SUCCS]:
                preds.append(bb_name_pred)
        preds_cfg[bb_name] = preds

    out = OrderedDict()
    for bb_name, triple_dict in succs_cfg.items():
        out[bb_name] = {INSTRS: triple_dict[INSTRS],
                        PREDS: preds_cfg[bb_name], SUCCS: triple_dict[SUCCS]}
    return out


def insert_into_cfg(new_header, backnodes, succ, cfg):
    assert type(new_header) == str
    assert type(succ) == str
    assert type(cfg) == OrderedDict

    # find all predecessors of succ
    predecessors = cfg[succ][PREDS]

    # add new_header to cfg
    # make its successor be succ
    # make its predecessors be the preds of succ
    safe_ret_label = {LABEL: f"safe.return.{new_header}"}
    new_ret = {OP: RET}
    new_label = {LABEL: new_header}
    new_jmp = {OP: JMP, LABELS: [succ]}
    cfg[new_header] = {PREDS: predecessors,
                       INSTRS: [safe_ret_label, new_ret, new_label, new_jmp], SUCCS: [succ]}

    # change succ's predecessor to new_header
    cfg[succ][PREDS] = [new_header]

    # change all predecessors of succ to point at new_header
    for pred in predecessors:
        # ignore backedge branch/jumps back to loop header
        if pred in backnodes:
            continue
        pred_successors = cfg[pred][SUCCS]
        new_successors = [new_header]
        for s in pred_successors:
            if s != succ:
                new_successors.append(new_header)
        cfg[pred][SUCCS] = new_successors
        new_jmp = {OP: JMP, LABELS: [new_header]}
        cfg[pred][INSTRS].append(new_jmp)


def join_cfg(cfg):
    assert type(cfg) == OrderedDict

    new_instrs = []
    for label, bb_dict in cfg.items():
        bb = bb_dict[INSTRS]
        if len(bb) != 0 and 'label' not in bb[0]:
            new_instrs.append({'label': label})
        elif len(bb) == 0:
            new_instrs.append({'label': label})
        for instr in bb:
            new_instrs.append(instr)
    return new_instrs


def reverse_cfg(cfg):
    new_cfg = OrderedDict()
    for basic_block in cfg:
        new_dict = {SUCCS: cfg[basic_block][PREDS],
                    INSTRS: cfg[basic_block][INSTRS],
                    PREDS: cfg[basic_block][SUCCS]}
        new_cfg[basic_block] = new_dict
    return new_cfg


def add_unique_exit_to_cfg(cfg, exit_name):
    preds_of_exit = []
    for basic_block in cfg:
        if cfg[basic_block][SUCCS] == []:
            preds_of_exit.append(basic_block)
            cfg[basic_block][SUCCS].append(exit_name)

    exit_dict = {SUCCS: [], INSTRS: [], PREDS: preds_of_exit}
    cfg[exit_name] = exit_dict
    return cfg


def form_cfg_w_blocks(func):
    return get_cfg_w_blocks(form_block_dict(form_blocks(func['instrs'])))


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
