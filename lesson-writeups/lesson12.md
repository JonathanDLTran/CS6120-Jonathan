# Summary

To run, run `yarn build`, `yarn unlink` and then `yarn link` after adding brili-tr to the config and build files. After this you can use the command `brench trace.toml > results-trace.csv` to see testing results. This runs all the benchmarks with the tracing program. To manually run a single test, you can do `bril2json < test-program | brili-tr {args} | python3 trace.py | brili -p {args}` to see the output of the test program, and also see dynamic bril instruction count. 

I implemented an ahead of time tracing optimizer. I go to the first non-main function in the program, trace until I hit the end of the function, e.g. a return, a call to another function, a call to print, or a memory operation. I then use this trace and optimize it using LVN, then stitch it back into the program. To stich, I simply add a speculate command, replace all branches with guards as appropriate, remove jumps, and finally add a commit. After, I add a jump to the correct location in the program, as required.

To test, I used the given benchmarks, and checked whether the results were the same before and after running the trace program. I had to fix a few bugs, such as how my LVN failed to handle floating point operations. This forced me to bail on optimizing floating point operations. It would likely be a quick fix to handle some of these floating point operations for LVN, modulo some algebraic simplifications that might cause accuracy problems. 

Another bug came up based on how I used guard expressions. Since the guard only fails when the condition is false, I had to track the runtime value of branches, and manually negate the condition (when the false branch is taken in tracing) so that the guard works properly when stitched into the original program.

# Results

Results were not great. The trace optimizer performs worse on every single benchmark. This is likely because my traces are very short, based on the conditions I have listed above. The short length of the trace does not allow lvn to do much optimization. It is also likely other optimizations besides LVN could be used as well, such as DCE, but I did not add this. Perhaps trying other optimizations like DCE would lead to more fruitful results.

Furthermore, my tracing is not interprocedural. I made this decision because I was not sure how to make guards jump to the right label in the correct function if the guard failed. If the tracing was interprocedural, the inlined code would allow for longer regions of code that could be optimized using LVN. It is likely some more code would be either redudant or removed entirely with longer traces. 

Finally, tracing only occurs in 1 function, for simplicity of implementation. It is likely that the first function I choose top optimise does not present many chances for optimzation to occur. It would be good to trace in as many functions as possible, then optimise all of these traces and stitch them into the original program. This would give as many chances as possible to optimize trace.
