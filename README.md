# CS 6120

This is a repository for implementation assignments for CS 6120.

The common workflow to run transformation passes and analyses on bril is 
`bril2json < test-name | python3 your-pass.py --options`.

# Optimizations
- Dead Code Elimination (Trivial, Aggressive, TODO: Mark and Sweep)
- Local Value Numbering / Global Value Numbering with Dominator Tree
- Loop Invariant Code Motion (Still testing)

# Analyses
- Live Variables 
- Reaching Definitions 
- Constant Propagation
- Available Expressions
- Dominator Analysis
- Dataflow Framework and Worklist Iterative Solver

# Utilities
- CFG construction / dot display
- Bril Language Utilities / Basic Interpretation

# Transformations
- To SSA and out of SSA

# Tests

To run all tests, run the command `bash run_all_tests.sh` in the main directory.
All subdirectories with the suffix "-tests" will be run on the appropriate programs.
