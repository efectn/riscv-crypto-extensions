#include <stdint.h>

#define UART_DATA (*(volatile uint32_t *)0x10000004u)

int main(void)
{
    int result = 12 + 30;

    UART_DATA = '0' + result / 10;
    UART_DATA = '0' + result % 10;
    UART_DATA = '\n';
    return 0;
}
