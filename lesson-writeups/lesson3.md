## Summary

I implemented trivial DCE with both the local deletion of overwritten instruction 
destinations within a basic block, and also added global deletion of unused variables.
To run these, you can use `python3 dce.py` for both optimizations, and 
`python3 dce.py -l` for local and `python3 dce.py -g` for global. 

I also implemented local value numbering with constant propagation, copy propagation, some basic simplification as an attempt to do common subexpression elimination and constant folding. All these optimization attempts are run
on the pass, and I did not add flags to individually enable these optimizations.

For constant propagation, every time a generated LVN value was a constant, instead
of returning the variable, I replaced it with a constant.

For copy propagation, every time an identity expression is generated, I replace
it with the previous variable it refers to. For instance
```
    x: int = const 4;
    y: int = id x;
    z: int = id y;
```
gets replaced with 
```
    x: int = const 4;
    y: int = id x;
    z: int = id x;
```

For common subexpression elimination, I implemented a simple approach to 
commutative expressions like addition or multiplication. This allows `add a b`
to be judged the same as `add b a`.

In the case of constant folding, I did simple interpretation. If all of the expression's arguments were already constants, I evaluated the expression completely. Otherwise, I returned the same expression, with no constants substituted.

## Testing

For testing, I first checked the generated code and any printed statements were correct
manually. I then ran these tests using turnt, to ensure correctness as more 
changes were made. 

Some of the tests are smaller and attempt to test certain features, such
as variables that are not used or variables that are immediately overwritten. 
Other tests combine multiple optimization opportunities. 

The lvn-dce-tests in particular leverage both lvn and dce opportunities,
and run the lvn, and then the dce pass, in order to clean up the code. 

The results of these tests can be found in the directories dce-tests, lvn-tests
and lvn-dce-tests. 

## Optimization

To check for optimizxation, I ran tests in the lvn-dce-tests directory. I paid attention
to whether the output was smaller than the input in terms of dynamic and static 
instructions. In general, I was pleased with the amount of redudancy that was eliminated. 

An example of this is the original program:
```
# ARGS: 1
@main(x: int) {
    x: int = add x x;
    x: int = const 4;
    x: int = const 5;
    y: int = id x;
    z: int = id y;
    w: int = id z;
    print w;
    a: int = add x y;
    b: int = add y x;
    print a;
    print b;
    c: int = mul x y;
    d: int = mul y x;
    e: int = add c d;
    f: int = mul e e;
    g: int = sub f c;
    print g;
    g: int = const 5;
    print g;
    f: int = const 4;
    print f;
    e: int = const 3;
    print e;
}
```
which can have constant propagation, copy propagation, constant folding and 
common subexpression elimination applied. There are also examples of dead code.

```
The result is:
@main(x: int) {
  x_2: int = const 4;
  x: int = const 5;
  print x;
  a: int = const 10;
  print a;
  print a;
  g_5: int = const 2475;
  print g_5;
  print x;
  print x_2;
  e: int = const 3;
  print e;
}
```
in which many of the assignments are removed, and the constants are able to be 
propagated effectively.

## Difficulties

Some of the difficulties I had included creating an unsound procedure for both dce
and lvn, dealing with arguments in LVN, as well as not dealing with division by 0.

For dce, when I split into basic blocks, I removed all variables as dead at the end
of a basic block. I realized these variables could persist past the end of a basic block
and fixed the problem appropriately.

In the case of lvn, I failed to take into account that variables can be reassigned
multiple times. I changed this by creating unique variable names, by adding on a
numerical index to the variable.

I also failed to deal with arguments in LVN correctly, initially. I later added
each argument into the LVN table before running the LVN optimization, to overcome
this problem.

For division by 0, I initially allowed the lvn pass to crash when the divisor was 0.
After the question raised in class, I changed this so that the compiler would
not raise an error or crash, and would instead just not optimize that specific 
instruction where the division by 0 occurs. The division by 0 will occur at runtime. 