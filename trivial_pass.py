import sys
import json


def main():
    prog = json.load(sys.stdin)
    print(prog)
    for func in prog["functions"]:
        new_instrs = []
        for instr in func["instrs"]:
            new_instrs.append(instr)
            new_instrs.append({'dest': 'new_var', 'op': 'const',
                               'type': 'int', 'value': 1})
            new_instrs.append({'args': ['new_var'], 'op': 'print'})
        func["instrs"] = new_instrs
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
