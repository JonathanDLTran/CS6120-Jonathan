import sys
import json


def dce(program):
    pass


def main():
    prog = json.load(sys.stdin)
    print(json.dumps(prog))


if __name__ == "__main__":
    main()
