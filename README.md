# CS 6120

This is a repository for implementation assignments for CS 6120.

The common workflow to run transformation passes and analyses on bril is 
`bril2json < test-name | python3 your-pass.py --options`.

# Tests

To run all tests, run the command `bash run_all_tests.sh` in the main directory.
All subdirectories with the suffix "-tests" will be run on the appropriate programs.