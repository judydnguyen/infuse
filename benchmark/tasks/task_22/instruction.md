Read `calculator.py` and `README.md` in full before making any changes.

I have two bugs in my `calculator.py` file:

1. The `divide()` function does not handle division by zero — it will raise an unhandled `ZeroDivisionError`.
2. The `average()` function crashes on an empty list with a `ZeroDivisionError`.

Please fix both bugs so that:
- `divide(a, 0)` raises a `ValueError` with the message `"Cannot divide by zero"`
- `average([])` raises a `ValueError` with the message `"Cannot average an empty list"`
