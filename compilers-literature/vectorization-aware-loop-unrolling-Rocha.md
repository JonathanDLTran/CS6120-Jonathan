# Vectorization Aware Loop Unrolling with Seed Forwarding

Rocha, Porpodas, Petoumenos et. al.

## Problem: 

SLP vectorization finds sequeneces of independent isomorphic instructions and converts it into a vector instruction. Do generate more vectorization opportunities, compilers use loop unrolling. However, compilers also want to avoid large code chunks, and so may also avoid unrolling, and thus miss vectorization of functions.

VALU is a method of doing loop unrolling, influenced by vectorization benefit. VALU does 2 things. First, VALU will analyze a loop, and see whether it can profit from unrolling and vectorization. Secondly, it also saves seed instructions that can be vectorized and givesit to SLP. This extra context allows for better vectorization in terms of searching for isomorphic def-use graphs.

## Approach

The main idea is to consider various loop unrollings, see if vectorization is profitable, and then do the unrolling, forward seed information to SLP, and allow SLP to use this seed information. First, a potential SLP graph is built.

## Evaluation

## Related Works