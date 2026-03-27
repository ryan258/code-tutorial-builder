def factorial(n):
    """Calculate factorial recursively."""
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)


def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a, b):
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result


if __name__ == "__main__":
    print(factorial(5))
    print(fibonacci(10))

    calc = Calculator()
    print(calc.add(3, 4))
    print(calc.multiply(5, 6))
    print(calc.history)
