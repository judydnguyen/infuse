from typing import List, Dict


class CalculatorError(Exception):
    pass


def add(a: float, b: float) -> float:
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise CalculatorError("division by zero")
    return a / b


def moving_average(values: List[float], window: int) -> List[float]:
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        raise ValueError("window larger than data")

    result = []
    for i in range(len(values) - window + 1):
        result.append(sum(values[i : i + window]) / window)
    return result


def normalize(values: List[float]) -> List[float]:
    if not values:
        raise ValueError("empty input")

    min_v = min(values)
    max_v = max(values)
    if min_v == max_v:
        return [0.0 for _ in values]

    return [(v - min_v) / (max_v - min_v) for v in values]


def summarize(values: List[float]) -> Dict[str, float]:
    if not values:
        raise ValueError("empty input")

    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def safe_compute(values: List[float], window: int) -> Dict[str, object]:
    """
    Composite function used by tests:
    - normalizes values
    - computes moving average
    - summarizes the result
    """
    normalized = normalize(values)
    ma = moving_average(normalized, window)
    stats = summarize(ma)

    return {
        "normalized": normalized,
        "moving_average": ma,
        "summary": stats,
    }