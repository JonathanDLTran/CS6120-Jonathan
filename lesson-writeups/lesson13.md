# Summary

I used the sketch builder from https://github.com/sampsyo/minisynth/blob/master/ex2.py, and built off this sketching program.

To add extra features, I considered adding comparison operators like less than, less than equal, greater than, greater than equal, equals and not equals. I then implemented these in ex2.py. 

I also added test sketches to see whether a solution could be synthesized for the holes. These included examples using the less than and greater than equals operator to check whether the sketch worked properly.

To do something different, I also added in simple structures that resemble for loops. These are the forplus, forminus, and fortimes loops. The gist is that `forplus x += n1 inrange n2` will add n1 to x for n2 number of times. This is defined similarly for the expressions forminus and fortimes. 

I unfortunately was not able to get fortimes to work the way I wanted to, perhaps because I had to convert bitvectors to ints and then back to bitvectors. Besides this though, forminus and forplus seem to work approrpriately and can be used to synthesize simple iteration.

In terms of test cases, for these small, contrived examples, the solver can find a solution relatively quickly. Most of the test cases are not very large, and the time to solve the sketch is minuscule. Even for the test case named large.txt, the time to solve the sketch is relatively quick, though this may be because the expression with holes is still syntactically similar to the expression without holes.

As a whole, this lesson was fairly straightforward given the code in ex2.py was already complete when I started with it. Adding on more elements was fairly simple, modulo some problems figuring out types in z3, which were quickly fixed by looking at the z3 documentation. Overall, I think synthesis seems remarkable, in that a program can be built without human intervention. I do have trouble seeing it being used in commonplace applications because it seems to scale poorly on larger sketch programs.