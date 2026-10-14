"""Simple calculator module."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    # BUG: no check for division by zero
    return a / b


def power(a, b):
    return a ** b


def average(numbers):
    # BUG: crashes on empty list
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    print(add(2, 3))
    print(divide(10, 2))
    print(average([1, 2, 3]))
