echo "Running Regression Tests"
echo "Reaching Definitions Tests"
turnt reaching-definitions-tests/*.bril
echo "Running CFG Tests"
turnt cfg-tests/*.bril
echo "Running LVN Tests"
turnt lvn-tests/*.bril
echo "Running DCE Tests"
turnt dce-tests/*.bril
echo "Running LVN & DCE Tests"
turnt lvn-dce-tests/*.bril