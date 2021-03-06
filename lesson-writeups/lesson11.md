# Summary

I implemented ismple reference counting for the Bril language, including the memory extension. To run, you can do `bril2json < test | brili-gc -p args`
replacing test and args appropriately. You will have to use the brili-gc typescript I wrote, run `yarn`, then `yarn build`, `yarn unlink` and then `yarn link` to have the executable for brili-gc.

In this assignment, because I focused on reference counting, I only needed to look at certain instructions. I considered id, alloc, free, store, load and ptradd instructions. To allow for the counting analysis, I created a map from pointers to the count for that pointer, and also created a map allowing pointers to point to another pointers. 

Free is trivial, and eliminated. Alloc adds a new pointer, and a counter is incremented to be 1. If there was a prior pointer to the variable that was given an allocation, that prior pointer is decremented. Anytime a decrement occurs, it is done recursively, such that if an object's counter reaches 0, if the object itself points to another object, that other object also has a recursive decrement operation applied. 

Stores cannot change the counters for any pointer. However, a store may allow a pointer to reference another pointer. The map of pointers pointing to other pointers is updated here. 

Loads can allow another variable to reference a pointer, if a pointer value ends up being loaded. This means loads increment a counter for a value if the value is a pointer.

Finally, if ptradd ends up assigning a different variable to a pointer, then the pointer gets its counter incremented appropriately.

# Testing

To test, I used brench to compare just the brili interpreter, versus the brili-gc interpreter, in which the free operation has no effect. I tested over every benchmark in the bril repository, and made sure the outputs were identical in both and there were no memory freeing issues. 

# Difficulties

Learning Typescript was a little difficult. In particular, I was not aware Typescript did not have keep types at runtime, which made it hard for me to figure out how to discriminate between various union types. I later ran into issues trying to figure out whether a value was a bigint, number or boolean, which caused some debugging trouble  as well. 

A problem more related to reference counting was how I needed to free all references at the end. Because reference counting is conservative, it leaves some references at the end that it cannot eliminate at runtime. I forgot to do this at the end of the program and had to add this in. 

I also initially failed to recursive update the counts for chains of pointers. I also had an issue where if I have a pointer to an array, I failed to check all the elements of the array, which could be pointers. I fixed this issue, by having the pointer map point to a list of potential pointers, which in the array example would be the instantiated pointers in the array.

Perhaps something that would be interesting to study would to figure out better schemes to do reference counting. In particular, it would be interesting to see if there are better places in the program to defer reference counting to. For example, rather than doing reference counting all at once, it would be interesting to do it at certain locations in the program.