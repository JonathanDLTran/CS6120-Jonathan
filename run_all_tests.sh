echo "Running Regression Tests"
echo "Reaching Definitions Tests"
turnt reaching-definitions-tests/*.bril
echo "Constant Propagation Tests"
turnt constant-propagation-tests/*.bril
echo "Live Variables Tests"
turnt live-variables-tests/*.bril
echo "Available Expressions Tests"
turnt available-expressions-tests/*.bril
echo "Running CFG Tests"
turnt cfg-tests/*.bril
echo "Running LVN Tests"
turnt lvn-tests/*.bril
echo "Running DCE Tests"
turnt dce-tests/*.bril
echo "Running LVN & DCE Tests"
turnt lvn-dce-tests/*.bril
echo "Running Dominator Utilities"
turnt dominator-utilities-tests/*.bril
echo "Running From SSA Tests"
turnt from-ssa-tests/*.bril
echo "Running To SSA Tests"
turnt to-ssa-tests/*.bril
echo "Running To LICM Tests"
turnt licm-tests/*.bril