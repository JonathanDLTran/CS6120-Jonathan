## Background

## Core Ideas

The core idea of the Superoptimizer paper is to use brute-force enumeration to find the smallest-sized program that is equivalent to the original program. The process of enumeration begins by considering all programs with 1 instruction, and seeing if the program is equivalent to the original program. If none of the programs of size 1 are equivalent to the original program, then programs composed of 2 instructions are considered. This process continues until an enumerated program is found to be semantically equivalent to the original program. By following this procedure, it is guaranteed that the discovered program will be the smallest program in size with the same behavior as the original program. 

One problem arising from brute force enumeration is the extended runtime needed to generate programs. Massalin proposes a method to eliminate programs that are clearly not minimal in size.

Brute force enumeration generates programs, but not all of these programs have the same semantic behavior as the original program. One way to ensure that the new enumerated program acts like the original program is to check it on every input. To do this, one can construct boolean minterms representing the original and the proposed program, and compare the minterms for equivalence. However, this technique fails to scale in terms of performance. In particular, the author notes that such a method only allows enumerations of programs with up to 3 instructions. Additionally, such a technique cannot apply to instructions that use pointers. Checking equivalence with pointers causes an doubly-exponential increase in the number of minterms that makes it infeasible to even compare minterms for limited memory machines. 

Massalin uses a clever technique to solve this problem. Since enumerated programs are likely to differ on many inputs from the original program, to eliminate semantically different programs, it suffices to create small test vectors as a filtering mechanism. Test vectors are manually chosen, and Massalin used test vectors that included edge cases for the type of program that was being tested, as well as more-general inputs ranging from -1024 to 1024. 

While test vectors are likely to eliminate many semantically different enumerated programs, some enumerated programs may still fall through the cracks. At this point, it is the responsibility of the operator of the Superoptimizer to manually ensure that the proposed program is equivalent to the original program. 

## Applications

## Related Works

