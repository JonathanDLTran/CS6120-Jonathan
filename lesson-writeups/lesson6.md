# Summary

I implemented to-SSA and from-SSA, and then tested the transformations to make sure they worked correctly. This included using them in a "round-trip" fashion. To check correctness of SSA form, I use the is_ssa function every time a transformation is done to make sure the program is a well-formed SSA program.

To try to remove more phi nodes, I tried global value numbering using the dominator tree approach as documented in Value Numbering by Briggs, Cooper and Simpson. I then added on aggressive dead code elimination from the powerpoint slides: http://www.cs.cmu.edu/afs/cs/academic/class/15745-s12/public/lectures/L14-SSA-Optimizations-1up.pdf

# Testing

I created tests as before for both the Bril to SSA pass and SSA back to normall brill pass. For the SSA back to normal Bril tests, I used tests from the original to-SSA output. I compared outputs without to-SSA, at the midpoint after to-SSA was run, and then after from-SSA was run, making sure they were identical.

For GVN testing, I wrote GVN tests and ran the GVN pass making sure the resutls were the same before and after. 

I also tried some larger programs, using the Bril benchmarks that use integer instructions, but not floats nor pointers. For these, I checked GVN on the program, making sure the result was the same as not running the pass.

# Optimization

For most of the Bril benchmarks, GVN was not able to identify much optimization potential. I instead wrote a DCE pass on top of the SSA to identify instructions that were dead. Initially, I wanted to use a worklist style algorithm to remove more instructions, but could not figure out the relationship between different basic blocks and which instructions could be killed. I eventually used the algorithm documented in: http://www.cs.cmu.edu/afs/cs/academic/class/15745-s12/public/lectures/L14-SSA-Optimizations-1up.pdf
as a means to find more dead instructions. Along the way, I discovered that this algorithm fails to work when there is a trivial infinite loop. I modified it to take into account all loops, by looking for any backedge in the graph. Therefore, the DCE algorithm I wrote identifies less dead instructions.

Interestingly, the DCE algorithm finds many dead instructions, most of which are Phi nodes that the GVN algorithm fails to eliminate. For example, running the  sum-divisors.bril benchmark with SSA using the command `bril2json < int-benchmarks/sum-divisors.bril | python3 ssa.py --to-ssa=True | brili -p 1000` yields 711 dynamic instructions. Running with dce enabled using the command `bril2json < int-benchmarks/sum-divisors.bril | python3 dce.py --adce=True | brili -p 1000` gives 513 dynamic instructions. Running with just gvn enabled using the command `bril2json < int-benchmarks/sum-divisors.bril| python3 gvn.py --gvn=True | brili -p 1000` gives 704 dynamic instructions. Running with gvn after the dce pass using the command `bril2json < int-benchmarks/sum-divisors.bril | python3 dce.py --adce=True | python3 gvn.py --gvn=True | python3 dce.py --adce=True| brili -p 1000` gives 511 dynamic instructions. Running DCE after GVN thereafter yields no further instruction cleanup. 

Perhaps it is not surprising to see that DCE cleans up so many instructions, because when using bril2txt to examine the optimized program, many of the original phi nodes created by the to-SSA pass are eliminated. Meanwhile, these phi nodes are no redudant, so they are not eliminated by GVN. 

However, all of these optimizations are actually end up adding instructions, as running `bril2json < int-benchmarks/sum-divisors.bril | brili -p 1000`, with no transformations actually gives 417 dynamic instructions total. The additional instructions created are likely from the added phi nodes that cannot be eliminated. 

# Challenges

One challenge was that I could not get brench to work. I wanted to compare the outputs,rather than the number of dynamic bril instructions executed, but I could not get this work.

Other challenges relate to SSA, where there were many edge cases, and I had to debug many different tests to get the implementation to work. Edge cases also caused issues in global value numbering, for example, with arguments, that did not have a number.

