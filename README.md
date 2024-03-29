# CS 6120

This is a repository for implementation assignments for CS 6120.

The common workflow to run transformation passes and analyses on bril is 
`bril2json < test-name | python3 your-pass.py --options`.

# Optimizations
- Dead Code Elimination (Trivial, Aggressive, TODO: Mark and Sweep)
- Local Value Numbering / Global Value Numbering with Dominator Tree
- Loop Invariant Code Motion 
- Induction Variable Elimination 
- Vectorization (Exceptionally Naive Version, Opportunistic LVN)

# Analyses
- Live Variables 
- Reaching Definitions 
- Constant Propagation
- Available Expressions
- Dominator Analysis
- Dataflow Framework and Worklist Iterative Solver
- Alias Analysis

# Utilities
- CFG construction / dot display
- Random CFG Construction
- Random Bril program construction
- Bril Language Utilities / Basic Interpretation / Builders / isa
  
# Transformations
- To SSA and out of SSA
- Loop Unrolling
- Store Movement, Constant Movement, Print Movement, Id Movement
- Aggressive Inlining (builds call graph, topologically sorts it, and inlines callees into callers whenever and wherever possible)
- TODO: Loop Fusion

# Infrastructure
- Sample LLVM Pass as part of Lesson 7, which implements a very basic form of inlining

# Garbage Collection
- A garbage collector in the reference collector style is implemented in brili-gc. This is in the bril fork. Recursive update of reference counters is supported.

# Synthesis
- Playing around with the idea of synthesis as covered in class and discussions
- TODO: Unrolling using synthesis?

# Extensions
- Bril Vector Extension with interpreter extension: use `brili-vc` for vector interpreter.

# Tests

To run all tests, run the command `bash run_all_tests.sh` in the main directory.
All subdirectories with the suffix "-tests" will be run on the appropriate programs.
