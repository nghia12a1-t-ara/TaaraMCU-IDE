"""
STM32 Project Templates
"""

# Default main.c for bare metal
MAIN_C_TEMPLATE = '''/**
 * @file main.c
 * @brief Main application entry point
 * @date {date}
 */

#include <stdint.h>

int main(void)
{{
    /* System initialization */
    
    /* Main loop */
    while (1)
    {{
        /* Application code */
    }}
    
    return 0;
}}
'''

# Blinky example
BLINKY_TEMPLATE = '''/**
 * @file main.c
 * @brief LED Blink Example for {mcu}
 */

#include <stdint.h>
#include "stm32f4xx.h"

/* LED Pin Configuration - Modify based on your board */
#define LED_PORT    GPIOA
#define LED_PIN     5

void delay_ms(uint32_t ms)
{{
    for (volatile uint32_t i = 0; i < ms * 4000; i++);
}}

void LED_Init(void)
{{
    /* Enable GPIO Clock */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    
    /* Configure LED Pin as Output */
    LED_PORT->MODER |= (1 << (LED_PIN * 2));
    LED_PORT->OTYPER &= ~(1 << LED_PIN);
    LED_PORT->OSPEEDR |= (1 << (LED_PIN * 2));
    LED_PORT->PUPDR &= ~(3 << (LED_PIN * 2));
}}

void LED_Toggle(void)
{{
    LED_PORT->ODR ^= (1 << LED_PIN);
}}

int main(void)
{{
    LED_Init();
    
    while (1)
    {{
        LED_Toggle();
        delay_ms(500);
    }}
    
    return 0;
}}
'''

# Makefile template
MAKEFILE_HEADER_TEMPLATE = '''PROJECT         := USER
PROJECT_DIR     := {project_dir}
FRAMEWORK_DIR   := {framework_dir}/STM32F4_Framework
SRC_DIRS        += $(PROJECT_DIR)/src
MODULE_LIST     := {modules}
PROJ_NAME       := {project_name}
'''
