import z3


def solve(phi):
    s = z3.Solver()
    s.add(phi)
    s.check()
    return s.model()


x = z3.BitVec('x', 8)
slow_expr = x * 2
h = z3.BitVec('h', 8)
fast_expr = x << h
goal = z3.ForAll([x], slow_expr == fast_expr)


y = z3.BitVec('y', 8)
n = z3.BitVec('n', 8)
goal = z3.ForAll([y], y * n == y)
print(solve(y << 3 == 40))
goal = (z3.Int('x') / 7 == 6)
print(solve(goal))
