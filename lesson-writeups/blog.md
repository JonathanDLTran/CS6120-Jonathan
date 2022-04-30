## Introduction

The majority of compilers utilize optimization to improve code, in terms of runtime performance, code size, and other factors. However, optimization does not necessarily generate the most optimal program; the optimization process merely generates a better candidate program. In the Superoptimization paper, a different paradigm is introduced: optimization is performed to generate the most minimal sized program, producing programs that are smaller compared to traditionally compiler-optimizer programs, as well as human hand-optimized programs.

As an illustration of Superoptimizer’s capabilities, consider an example centered on compiling the signum function, which is defined as 
```int signum(x) {
	If (x > 0) return 1;
	Else if (x <  0) return -1;
	Else return 0;
}
```
The author notes this program usually compiles to around 9 instructions, including several condition jumps, while a human can hand-optimize this program to be 6 instructions. Remarkably, Superoptimizer finds an even smaller solution, consisting of four instructions, which is shown below.
```
Add.l d0, d0
Subx.l d1, d1
Negx.l d0
Addx.l d1, d1
```
This solution is guaranteed to use the least number of instructions to calculate the signum function, and avoids the use of any conditional jumps. Assuming this function is used many times, the impact of the Superoptimizer is tremendous, by shaving off 50% of instructions from a non-optimized solution, and also improving on pipelined execution, due the lack of jumps. Further, we know that in the above architecture, there is no shorter instruction solution, so there is no need for further optimization. As a result of this example, we can see the power of using the Superoptimizer.  

The Superoptimizer can be generalized to be used in a variety of circumstances, ranging from commonly used mathematical routines, to chunks of code that have high usage. The author gives several examples ranging from architectural design to generating pruning sequences for the superoptimizer itself. 

Finally, the ideas introduced by the Superoptimizer are used in various other works today, and continue to influence research in compiler optimizations. The brute force search method used in the Superoptimizer has been refined in various ways, ranging from rule-guided search in the Denali compiler, to stochastic search used by STOKE. The optimality of Superoptimizer’s generated code has been used to create “libraries” of peephole optimizations that can be applied by real world compilers. All of these works build upon the ideas introduced by the Superoptimizer to address deficiencies and build even better compilers. 

## Core Ideas

The core idea of the Superoptimizer paper is to use brute-force enumeration to find the smallest-sized program `P’` that is equivalent to the original program `P`. The process of enumeration begins by considering all programs with 1 instruction, and seeing if the program is equivalent to the original program. If none of the programs of size 1 are equivalent to the original program, then programs composed of 2 instructions are considered. This process continues until an enumerated program is found to be semantically equivalent to the original program. By following this procedure, it is guaranteed that the discovered program will be the smallest program in size with the same behavior as the original program. 

One problem arising from brute force enumeration is the extended runtime needed to generate programs. Massalin proposes a method to eliminate programs that are clearly not minimal in size, a technique called pruning. Sequences of instructions that have no effect on the program, or are redundant, are recorded. Whenever an enumerated program contains these sequences, the program is not considered, because it is not minimal. 

For example, an instance of pruning occurs with the series of instructions `move x y; move x y`. The first instruction is identical to the second, and so the combined effect is equivalent to just a single move instruction. When pruning is used, this redundancy, and others like it, are eliminated from program enumeration. 

Brute force enumeration generates programs, but not all of these programs have the same semantic behavior as the original program. One way to ensure that the new enumerated program acts like the original program is to check it on every input. To do this, one can construct boolean minterms representing the original and the proposed program, and compare the minterms for equivalence. However, this technique fails to scale in terms of performance. In particular, the author notes that such a method only allows enumerations of programs with up to 3 instructions. Additionally, such a technique cannot apply to instructions that use pointers. Checking equivalence with pointers causes an doubly-exponential increase in the number of minterms that makes it infeasible to even compare minterms for limited memory machines. 

Massalin uses a clever technique to solve this problem. Since enumerated programs are likely to differ on many inputs from the original program, to eliminate semantically different programs, it suffices to create small test vectors as a filtering mechanism. Test vectors are manually chosen, and Massalin used test vectors that included edge cases for the type of program that was being tested, as well as more-general inputs ranging from -1024 to 1024. 

While test vectors are likely to eliminate many semantically different enumerated programs, some enumerated programs may still fall through the cracks. At this point, it is the responsibility of the operator of the Superoptimizer to manually ensure that the proposed program is equivalent to the original program. 

## Applications

The author proposes several scenarios where Superoptimizer can be applied. The simplest scenarios are 

## Related Works

Massalin’s work is seminal, because it is the first to consider truly optimal programs, rather than incremental improvements that constitute most compiler optimizations. Being able to find optimal real world programs such as the signum function was a major success of Massalin’s work. However, Superoptimizer has several downsides. One of the major limitations of Massalin’s work is that Superoptimizer takes a long time to run and find optimal programs. Another downside is that Superoptimizer only works on the Motorola 68000 and Intel 8086 architectures. Finally, yet another issue with Superoptimizer is that enumerated programs are not guaranteed to be equivalent to the original program. These downsides are dealt with in other works that build upon ideas found in Superoptimizer. 

For instance, the GNU Superoptimizer project made the Superoptimizer project 
