## Summary

I implemented dataflow analysis using the worklist algorithm covered in class. I implemented several analyses that seemed interesting to me: reaching definitions, constant propagation, live variables and available expressions. For each of the these analyses, I wrote test cases and used turnt as a regression testing system to make sure changes I made did not break previously checked test outputs.  

The dataflow analyses can be ran by running `python3 dataflow.py --reaching=True --constant=True --live=True --available=True` with appropriate flags being turned off as needed. To run the turnt tests, choose the appropriate testing directory and run `turnt test-direct/*.bril`. 

## Testing

I wrote different test programs for each of the analyses. 

## Results

## Difficulties

When I first started, I had trouble understanding the live variables analysis. It took me a bit of time to understand live variables would be variables that were defined, and would have their value used sometime in the future. Another problem I faced was for the available expressions analysis, where I associated each expression with a value, like those calculated in local value numbering. I later realized the available expressions should be thought as combinations of variables that you do not want to recompute. 