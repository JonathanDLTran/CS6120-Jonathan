for file in all-benchmarks/*.bril; 
do  
    echo $file
    bril2json < $file | brili-tr > trace.json
    bril2json < $file | python3 trace.py | brili > first.txt
    bril2json < $file | brili > second.txt
    diff first.txt second.txt
done 