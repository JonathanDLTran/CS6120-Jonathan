# Summary

I implemented a simplified version of what inling would look like, except that to make it simpler to implement, I limited the function to inline into to be main, and functions that would be inlined could only be 1 basic block long and have exactly 1 return instruction. Further, the functions to inline cannot contain any other calls to any other functions. All these conditions trivialize the pass I have written. To make it more robust, one might want to consider functions that have multiple basic blocks, many exit point and possibly has calls to other functions, that does not form a loop in the call graph. 

I did this using a module pass, where I first read over all functions and check if it is main or not. For functions that are not main, I check if they satisfy the conditions I mentioned previously. For those functions that satisfy the conditions I wanted, I then inline the function into the main function, by setting up a builder, then copying instructions one by one. I make sure to change the arguments of the functions to be the values from the main function, and then I set the return function's arguments as well to change its uses to be the correct ones in the main function.

# Testing

I tried the program on a simple test case, where the function to be inlined was a simple addition function, that adds 2 integers and returns the sum. This addition function can be seen in `test.c`. To run this, try `bash run.bash test.c`, which prints out 3 results of 3 calls. Note that the 2 calls to add are fully inlined (it comes out to be about 7 instructions for each to be inlined).

I then try on a real world program, specifically on conway's game of life. I use an implementation from https://rosettacode.org/wiki/Conway%27s_Game_of_Life#C, and all credit should go to this source.

Running `bash run.bash conway.c` will execute the program, showing the game working as intended.
There's no effect by the inling on the conway program as my inlining program is very simple, and rejects any inling attempts for this conway program.

# Challenges

LLVM was challenging to work with. Reading the LLVM documentation was tricky, as I often had to search various LLVM doxygen pages until I found the information needed. In terms of using LLVM, there were several troubles I encountered. First, I realized late on that I needed to clone instructions, rather than to reuse them. Next, I also realized I had to insert instructions after iteration, because that would avoid changing the iterator. I often forgot about checking for terminator blocks, which made some bugs initially occur. Removing instructions is also difficult, as one needs to remove all of the uses of that instruction before the instruction can be deleted. Finally, trying to figure out how to set up a module pass was tricky. I searched online, found a stackoverflow post, and that post finally led me back to Issue #7 on the llvm for grad students repository. 