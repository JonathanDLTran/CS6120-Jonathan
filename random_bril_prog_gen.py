"""
Randomly Generates Well-Formed Core-Bril programs 

To be used for compiler fuzzing tests.

Workflow is: 
1. Generate Random CSmith Program (with print statements of variables)
2. Run Random program on reference interpreter
3. Compare results of running random program on rerference interpeter,
after transformation pass
(Can use md5 checksum to compare, as CSmith does.)

Kind of the same idea as CSmith, except much simpler,
and we have a (hopefully) correct reference interpreter
to check the result of the untransformed and transformed programs
"""
