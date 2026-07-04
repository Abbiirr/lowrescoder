package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    private final Calculator calc = new Calculator();

    @Test
    void testAdd() {
        assertEquals(5.0, calc.add(2, 3));
    }

    @Test
    void testSubtract() {
        assertEquals(1.0, calc.subtract(3, 2));
    }

    @Test
    void testMultiply() {
        assertEquals(6.0, calc.multiply(2, 3));
    }

    @Test
    void testDivide() {
        assertEquals(2.5, calc.divide(5, 2));
    }

    @Test
    void testDivideByZero() {
        assertThrows(ArithmeticException.class, () -> calc.divide(1, 0));
    }
}
