
"""Basic calculator functions used by the Flask app and pytest suite."""


def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def subtract(a, b):
    """Return the difference between two numbers."""
    return a - b


def multiply(a, b):
    """Return the product of two numbers."""
    return a * b


def divide(a, b):
    """Return the quotient of two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


def calculate(a, b, operation):
    """Run the requested calculator operation."""
    operations = {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide,
    }

    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")

    return operations[operation](a, b)


class Calculator:
    """Optional class-based interface for the same calculator behavior."""

    @staticmethod
    def add(a, b):
        return add(a, b)

    @staticmethod
    def subtract(a, b):
        return subtract(a, b)

    @staticmethod
    def multiply(a, b):
        return multiply(a, b)

    @staticmethod
    def divide(a, b):
        return divide(a, b)
