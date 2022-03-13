#include <stdio.h>

int branch(int a) {
    if (a > 0) {
        return 10;
    } else {
        return 20;
    }
}
int add(int a, int b) { return a + b; }
int main(void) {
    int result1 = add(0, 1);
    int result2 = branch(-5);
    int x = 4;
    int y = 5;
    int result3 = add(x, y);
    printf("%d\n", result1);
    printf("%d\n", result2);
    printf("%d\n", result3);
    return 0;
}