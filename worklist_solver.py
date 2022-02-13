"""
Generic Worklist Data Flow Solver
"""
from collections import OrderedDict


class Worklist(object):
    def __init__(self, entry, cfg, blocks, init, merge, transfer) -> None:
        self.entry = entry
        self.cfg = cfg
        self.blocks = blocks
        self.init = init
        self.merge = merge
        self.transfer = transfer

    def get_predecessors(self, block_name):
        cfg = self.cfg
        preds = set()
        for other_block_name, succs in cfg.items():
            for s in succs:
                if s == block_name:
                    preds.add(other_block_name)
                    break
        return list(preds)

    def solve(self):
        in_dict = OrderedDict()
        for name in self.blocks:
            if name == self.entry:
                in_dict[self.entry] = self.init
            else:
                in_dict[name] = set()
        out_dict = OrderedDict()
        for name in self.blocks:
            out_dict[name] = self.init

        worklist = [(name, self.blocks[name]) for name in self.blocks]
        while worklist != []:
            (block_name, block) = worklist.pop()
            pred_names = self.get_predecessors(block_name)
            preds = []
            for name, _ in self.blocks.items():
                if name in pred_names:
                    preds.append(out_dict[name])
            # if no preds, it is the entry location. Add args as needed.
            if preds == []:
                if len(in_dict[self.entry]) != 0:
                    preds.append(in_dict[self.entry])
            in_b = self.merge(preds)
            in_dict[block_name] = in_b
            new_out_b = self.transfer(in_b, block)
            old_out_b = out_dict[block_name]
            if new_out_b != old_out_b:
                successor_names = self.cfg[block_name]
                successors = []
                for succ_name, succ_blocks in self.blocks.items():
                    if succ_name in successor_names:
                        successors.append((succ_name, succ_blocks))
                worklist += successors
            out_dict[block_name] = new_out_b
        return (in_dict, out_dict)
