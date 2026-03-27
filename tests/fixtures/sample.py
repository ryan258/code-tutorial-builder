import math


def greet(name):
    """Say hello to someone."""
    print(f"Hello, {name}!")


class Counter:
    """A simple counter."""

    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1


if __name__ == "__main__":
    greet("world")
    c = Counter()
    c.increment()
