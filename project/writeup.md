# Auto-Vectorization for Bril

## Introduction

In this project, I sought to bring auto-vectorization to the Bril language. I adde a basic vector instruction set to the Bril language and implemented it in the reference interpreter as `brili-vc`. I then implemented various approaches towards vectorization, beginning with a naive form of vectorization that 

## Vector Language

The design of the vector language was based off resources from several students who had previously taken CS 6120, as well as the LLVM vector language. The students' languages are located at [vril](https://www.cs.cornell.edu/courses/cs6120/2019fa/blog/vril-vector-bril/), and [vector-instruction-support](https://www.cs.cornell.edu/courses/cs6120/2019fa/blog/interpreter-vector-support/). The LLVM vector language can be found be found at [llvm-vector](https://llvm.org/docs/LangRef.html#vector-operations).

Using these resources, I specified a minimal vector language. Each vector is comprised of exactly 4 ints. To create a fresh vector, one can use the `veczero` command, which creates a vector with all lanes starting with a value of 0.  Operations on vectors include `vecadd`, `vecsub`, `vecmul`, and `vecdiv`, which are similar to their single integer Bril counterparts, except thtat these operations operate on 4 integers at a time. `vecmove` copies the value in one vector register to another vector register. `vecmac` represents an operation multiplying two vectors, and then adding a vector offset. `vecneg` negates all the elements of a vector. Due to project limitations, neither `vecmac` nor `vecneg` were handled; however, it is possible to extend the vectorization to handle these 2 instructions. 

To interact between vector registers and normal registers. one can load into and store from vectors. For instance, the `vecload` instruction places one integer of data into a vector, at the specified index in the vector. Likewise, `vecstore` extracts one integer of data from a vector into a Bril pseudo-register. 

The vector language is simulated in the Bril interpreter. I implemented the vector registers as variables storing array of width 4. Each vector operation manipulates the array appropriately; for instance, `veczero` instantiates all the cells of the array to have value 0, `vecload v i d` loads data `d` into the array representing vector `v` at index `i` in the array, and `vecadd v1 v2` does element-wise addition on the arrays representing vectors `v1` and `v2`. The implementation of this interpreter is located in the files `bril-vc` and `brili-vc`.

## Vectorization

## Evaluation

## Conclusion
