ARGS = "args"
DEST = "dest"
LABELS = "labels"
TYPE = "type"
OP = "op"
VALUE = "value"
LABEL = "label"
FUNCS = "funcs"


INT = "int"
BOOL = "bool"


CONST = "const"


ADD = "add"
SUB = "sub"
MUL = "mul"
DIV = "div"


EQ = "eq"
LT = "lt"
GT = "gt"
LE = "le"
GE = "ge"


NOT = "not"
AND = "and"
OR = "or"


JMP = "jmp"
BR = "br"
CALL = "call"
RET = "ret"


ID = "id"
PRINT = "print"
NOP = "nop"


BRIL_BINOPS = [
    ADD, SUB, MUL, DIV,
    EQ, LT, GT, LE, GE,
    AND, OR,
]

BRIL_UNOPS = [NOT]


BRIL_CORE_INSTRS = [
    *BRIL_BINOPS, *BRIL_UNOPS,
    JMP, BR, CALL, RET,
    ID, PRINT, NOP,
]

BRIL_COMMUTE_BINOPS = [
    ADD, MUL, AND, OR, EQ
]


def build_unop(unop, arg):
    pass


def build_binop(binop, arg1, arg2):
    pass
