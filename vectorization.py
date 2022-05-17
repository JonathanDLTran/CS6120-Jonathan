"""
Automatic Vectorization

TODO
- First: preprocess: If __No-Mem Ops__, then run DCE, GVN and LICM 
- Second: run alias analysis if there are Mem Ops
- Third: Loop Unroll as Much as Possible
- Fourth: Run Function Block Coalescing to remove as many labels and jumps
---------
Vectorization
- Use ideas from SLP Paper
    - Heuristic?
"""
