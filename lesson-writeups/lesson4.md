## Links

Programs are at:
Tests are at:

## Summary

I implemented dataflow analysis using the worklist algorithm covered in class. I implemented several analyses that seemed interesting to me: reaching definitions, constant propagation, live variables and available expressions. For each of the these analyses, I wrote test cases and used turnt as a regression testing system to make sure changes I made did not break previously checked test outputs.  

The dataflow analyses can be ran by running `bril2json < test-name | python3 dataflow.py --reaching=True --constant=True --live=True --available=True` with appropriate flags being turned off as needed. To run the turnt tests, choose the appropriate testing directory and run `turnt test-direct/*.bril`. 

## Testing

I wrote different test programs for each of the analyses. In general, I aimed to see that specific features of each analysis were correct. For instance, for the liveness analysis, I created tests that make sure that variables defined in one basic block would
be marked as live at the end of the basic block if there were no redefinitions. For available expressions, I made example tests where different branches might have some expression, like `x + y` defined one branch, but not another, which would not propagate
the expression `x + y` to the next block succeeding both branches. Similarly, I did the same for constant propagation, where one branch might have a variable `x` holding the value 3, while another may have `x` holding a value 4.

I then used turnt testing at the end to make sure changes I made in the programs did not change the results of the test to be incorrect. 

## Results

In terms of results, for this task, reviewed my results from each test and made sure
that the analysis was correct. For instance, for the test:
```
@main() {
    a: int = const 3;
    b: bool = const true;
    br b .first .second;
.first:
    a: int = const 4;
    jmp .end;
.second:
    a: int = const 5;
    jmp .end;
.end:   
    a: int = const 6;
    print a;
    print b;
    c: int = add a a;
    print a;
}
```
I checked the output:
```
Function: main
In:
	b0: No Reaching Definitions.
	first: a on line 1.
	first: b on line 2.
	second: a on line 1.
	second: b on line 2.
	end: b on line 2.
	end: a on line 5.
	end: a on line 8.
Out:
	b0: a on line 1.
	b0: b on line 2.
	first: b on line 2.
	first: a on line 5.
	second: b on line 2.
	second: a on line 8.
	end: b on line 2.
	end: a on line 11.
	end: c on line 14.
```
which I checked to be make sense relative to the definitions we had be given. 

## Difficulties

When I first started, I had trouble understanding the live variables analysis. It took me a bit of time to understand live variables would be variables that were defined, and would have their value used sometime in the future. Another problem I faced was for the available expressions analysis, where I associated each expression with a value, like those calculated in local value numbering. I later realized the available expressions should be thought as combinations of variables that you do not want to recompute. 

Interestingly, making the worklist solver was not too complicated, though that might be because I used python. I can imagine using another language like OCaml would make the worklist solver more difficult to parametrize, especially depending on what containers or functions one chooses to use. 