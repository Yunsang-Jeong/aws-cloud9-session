#include <stdio.h>

int main(void){
    int num1, num2, sum;

    printf("Intput first number: ");
    scanf("%d", &num1);

    printf("Intput second number : ");
    scanf("%d", &num2);

    sum = num1 + num2;

    printf("Sum:%d\n", sum);

    return 0;
}