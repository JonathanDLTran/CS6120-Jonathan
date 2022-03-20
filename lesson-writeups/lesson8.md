# Summary

For this lesson, implemented loop invariant code motion. I tested the reuslts against a small test suite I wrote, and then also used the brenchmarks for the Bril core language as testing. In addition, I also used the same benchmarks to measure the impact of optimization. The optimization itself can be run via `bril2json < benchmark | python3 licm.py --licm=True | brili -p {args}`. To see the results on the benchmarks, one can also run `brench licm.toml > results-licm.csv` to get results in CSV form.

I had some challenges along the way, such as changing all jumps to the loop preheader rather than to the header in the case of backedges in the loop. This caused the optimization to perform poorly, and once I realized this mistake, fixing it also showed a performance improvement on the benchmarks.

Writing the tests also revealed another challenge, in which I had problems trying move instructions out from the loop to the preheader. I found that I needed to move instructions from the loop in a specific order, where the operands to a instruction had to already be moved, before the instruction could be moved.

Another issue is dealing with nested loops. At the present moment, I do not distinguish between inner loops and outer loops, with the inner loop nested in the outer one. Doing an optimization on the inner loop first might allow instructions moved to the inner loop's preheader to be once again moved to the preheader of the outer loop, allowing for further optimization impact. 

As an aside, to learn more about loop optimization, which I found interesting, I also choose to implement induction variable elimination, which I tested on some trivial examples to see whether it could detect simple instances of induction variables. Because I did not implement the optimizations to target the Memory extension of the Bril language, the induction variable elimination effect is much more limited. For this optimziation, I also faced challenges, many of them pertaining to what kinds of basic induction variables I could detect, and how I could move their definitions.

# Optimization Results

I found that the loop invariant code motion optimization was able to achieve an average of 3.5% improvement in the number of dynamic Bril instructions executed by the interpreter (with standard deviation of 5.6%), when compared to running the benchmark without loop invariant code motion. I use the same arguments that the benchmark writer speicified. The results come from evaluating the optimization on the Bril benchmarks that only use the Bril core language (Excluding Floating Point extensions and Memory Extensions). Because I measure the number of dynamic instructions using the interpreter, I do not have to measure many runs (unlike measuring an LLVM optimization, which when run on a machine, would have variability in timing.)

A sample of the table with the data is included here, to avoid making the post too large, but note that this sample is not representative across all benchmarks, it is just the first 8 on my benchmarks ordering:

Here benchmark refers to the benchmark name, run is either baseline, referring to the benchmark without loop invariant code motion applied, licm refers to the benchmark with loop invariant code motion applied, and result is the number of reported dynamic instructions when the brili interpreter is used. 

| benchmark | run | result |
| --------- | --- | ------ | 
| quadratic | baseline | 785 |
| quadratic | licm | 703 | 
| primes-between | baseline | 574100 |
| primes-between | licm | 491191 |
| orders | baseline | 5352 |
| orders | licm | 4928 |
| relative-primes | baseline | 1923 | 
| relative-primes | licm | 1858 |
| check-primes | baseline | 8468 |
| check-primes | licm | 8058 |
| sum-sq-diff | baseline | 3038 |
| sum-sq-diff | licm | 2840
| loopfact | baseline | 116 |
| loopfact | licm | 101 |
| recfact | baseline | 104 |
| recfact | licm | 104 |

A plot is also shown in the repository, and the full CSV is also in the repository.

Overall, across all the benchmarks evaluated, Loop Invariant Code Motion reported no increase in the number of dynamic instructions. Indeed, for a majority of the benchmarks (15 of the 23 benchmarks), the number of dynamic insturctions executed was exactly the same as the number of dynamic instructions executed for the baseline. For a 8 of the 23 total benchmarks, a decrease in number of dynamic optimizations was achieved. For the benchmarks where a decrease was observed, the decrease was generally a result of pulling out instructions that were defining constants; these constants were then removed to the loop header, thus decreasing dynamic instruction count. 

Some limitations of these measurements is that working with dynamic instruction count fails to take into account other factors into the time the program executes. For instance, branching can affect the time by forcing the instruction pipeline to be flushed, and instructions may not all take the same amount of time to execute. 

In summary, the loop invariant code motion optimization improves performance of Bril Core programs by sometimes decreasing the number of dynamic instructions executed. A more interesting analysis would be to see if further optimization can be achieved by pairing loop invariant code motion with other optimizations, that eliminate dead code in the loops, or whether there are different loop scenarios that can be optimized even further. 



