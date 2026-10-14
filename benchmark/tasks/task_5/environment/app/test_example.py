import pytest
from example import (
    add,
    divide,
    moving_average,
    normalize,
    summarize,
    safe_compute,
    CalculatorError,
)


# -----------------------------
# Basic arithmetic
# -----------------------------
def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0.5, 0.25) == 0.75


def test_divide():
    assert divide(10, 2) == 5
    assert divide(-4, 2) == -2


def test_divide_by_zero():
    with pytest.raises(CalculatorError):
        divide(1, 0)


# -----------------------------
# Moving average
# -----------------------------
def test_moving_average_basic():
    values = [1, 2, 3, 4]
    assert moving_average(values, 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_one():
    values = [5, 6, 7]
    assert moving_average(values, 1) == [5, 6, 7]


def test_moving_average_invalid_window():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)
    with pytest.raises(ValueError):
        moving_average([1, 2], 3)


# -----------------------------
# Normalization
# -----------------------------
def test_normalize_basic():
    values = [2, 4, 6]
    result = normalize(values)
    assert result == [0.0, 0.5, 1.0]


def test_normalize_all_same():
    values = [3, 3, 3]
    result = normalize(values)
    assert result == [0.0, 0.0, 0.0]


def test_normalize_empty():
    with pytest.raises(ValueError):
        normalize([])


# -----------------------------
# Summary stats
# -----------------------------
def test_summarize():
    values = [1, 2, 3, 4]
    stats = summarize(values)
    assert stats["min"] == 1
    assert stats["max"] == 4
    assert stats["mean"] == 2.5


def test_summarize_empty():
    with pytest.raises(ValueError):
        summarize([])


# -----------------------------
# Composite function
# -----------------------------
def test_safe_compute():
    values = [1, 2, 3, 4]
    result = safe_compute(values, window=2)

    assert "normalized" in result
    assert "moving_average" in result
    assert "summary" in result

    assert result["moving_average"] == [0.16666666666666666, 0.5, 0.8333333333333333]
    assert result["summary"]["min"] >= 0.0
    assert result["summary"]["max"] <= 1.0


def test_safe_compute_invalid_window():
    with pytest.raises(ValueError):
        safe_compute([1, 2, 3], window=0)