cd build
make
cd ..
/usr/local/opt/llvm/bin/clang -Xclang -load -Xclang build/skeleton/libSkeletonPass.* test.c
./a.out