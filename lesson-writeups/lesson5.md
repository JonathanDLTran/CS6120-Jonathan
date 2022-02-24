## Summary

I implemented the dominator utilities suggested in lesson 5, finding the dominators of a node, the strict dominators, the immediate dominator, the dominator tree and the dominance frontier. 

I followed the pseudocode and definitions for each of these constructs from the lesson 5 page, almost exactly as stated. For the most part, I found that these definitions worked intuitively, and the algorithm appeared to work, except for some small situations I discovered during testing.

## Testing

I wrote several test programs to check my implementation of the utilities. These programs have different structures, such as loops that include the entry, unreachable blocks of code, and one that is a small web of basic blocks. I made these programs small so that I could verify the result manually, by calculating each of these dominator results by hand, and then checking with the program's calculated results.

## Results

Here's a simple program that I caused me some trouble with debugging my implementation:
```
@main{
.cycle:
    jmp .next;
.next:
    jmp .cycle;
}
```
and the results
```
Dominators
	cycle is dominated by:	[cycle]
	next is dominated by:	[cycle, next]
Dominator Tree
digraph main {
  cycle;
  next;
  cycle -> next;
}
Dominance Frontier
	cycle:	[cycle]
	next:	[cycle]
```
Something left desired is making larger CFGs to test on, and making these CFGs be examples of "tricky" edge cases.

## Difficulties

Implementing dominators ended up being a bit trickier than I imagined. In particular, I was caught off guard by some edge cases when computing dominators, which ended up exposing some confusion that I had with the dominator definitions. This caused me to change some implementational details when calculating dominators. For example, I wrote an example program where the CFG consists of 2 basic blocks (A and B, A being an entry), forming a loop. The naive algorithm computes A as being dominated by both B and A, while B is dominated both A and B. This does not make sense as the path from the entry to the entry does not include B in it. I changed the algorithm to only consider A to be dominated by itself. 

Another problem arising over computation of dominators is with unreachable blocks of code. By definition, these unreachable blocks of code should be dominated by every basic block, since there is no path from the entry to these unreachable blocks. However, this produces unintuitive results later on, when computing the dominator tree and the dominance frontier. I decided to do a DFS to find all the reachable blocks of code, and set the dominators of all unreachable blocks to be only the entry block of the CFG. I don't think this is a justified decision, though it appears to give more intuitive results when calculating dominance frontiers in testing.

I also had a few issues with finding a unique immediate dominator, but this was fixed through some debugging, and realizing that I had implemented one of the subalgorithms incorrecrly. 