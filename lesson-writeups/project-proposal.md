# What will you do?

I want to add a vector instruction set to the Bril language, and implement a vectorization pass that finds opportunities to vectorize Bril IR code into a parallel form. The vector width would be fixed in advance. In particular, I plan to write a simple vectorizer pass that detects whether operations inside a program can be vectorized together. 

Depending on how much the scope of this project is, if the scope is too small, I would try implementing the polyhedral model for loop optimization, to try to achieve further vectorization, within loops. If this ends up being the case, I will read over lecture nodes/slides relating to the polyhedral model. I need to catch up on aspects of linear programming and integer programming. I would aim to reproduce a basic optimization like Martin Griebl documented as the space-time transformation in https://www.infosun.fim.uni-passau.de/cl/loopo/doc/loopo_doc/node3.html.

These notes seem promising:
https://polyhedral.info/ - from an older version of CS 6120
https://homes.luddy.indiana.edu/achauhan/Teaching/B629/2010-Fall/StudentPresns/PolyhedralModelOverview.pdf
https://events.csa.iisc.ac.in/summerschool2013/slides/automatic-parallelization-introduction-polyhedral-models.pdf

# How will you do it?

I plan to extend the Bril interpreter to have a vector instruction, with vector operations like vector addition and vector multiplication, concatenation of vectors, as well as loads and stores into and from vectors. This would involve changing the Bril Json Parser and also involving changing the typescript interpreter. 

I will be working with the Bril memory extension, to allow for interaction with arrays and pointers in the Bril language. In order to check for vectorization opportunities, I will implement alias analysis for Bril, to see if vectorization can be done. I would start by following the alias analysis defined in lecture, and try expanding to other forms like Steensgard's alias analysis algorithm. 

I will try to detect whether a loop can be unrolled, and unroll the loop as much as possible to enable further vectorization inside the loop. If not possible to unroll the whole loop, I will unroll the loop by some number of fixed iterations, say 4 iterations at a time.

If I move on to working on the polytope method, I would also have to add utilities to identify for loops and their format, and also represent the polyhedron and allow for transformations on the polyhedron. 

# How will you empirically measure success?

I will either create my own benchmarks or choose some common benchmarks, and translate these benchmarks into bril. I will look for benchmarks that focus on loops, with arrays inside the loop.

Since I am working at the Bril level, I am planning to count the number of vector instructions generated in each pass. The more vector instructions emitted, the more successful the pass.

I might also come up with a cost model that evaluates the cost of each vector instruction and regular instruction. This way, the optimized and unoptimized programs can be compared based on the result of the cost model. 

