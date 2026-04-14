import pytest

from calculator import Calculator, add, calculate, divide, multiply, subtract

ADD_CASES = [
    pytest.param(8, 2, 10, id="small_positive"),
    pytest.param(-4, -2, -6, id="negative_pair"),
    pytest.param(9, 2, 11, id="odd_plus_even"),
    pytest.param(180, -69, 111, id="mixed_large"),
]

SUBTRACT_CASES = [
    pytest.param(8, 2, 6, id="small_positive"),
    pytest.param(8, 4, 4, id="balanced"),
    pytest.param(11, 2, 9, id="odd_minus_even"),
    pytest.param(-10, 2, -12, id="negative_result"),
]

MULTIPLY_CASES = [
    pytest.param(8, 2, 16, id="small_positive"),
    pytest.param(5, 2, 10, id="whole_number"),
    pytest.param(9, 2, 18, id="odd_times_even"),
    pytest.param(-6, -4, 24, id="negative_pair"),
]

DIVIDE_CASES = [
    pytest.param(8, 2, 4, id="small_positive"),
    pytest.param(4, 2, 2, id="whole_number"),
    pytest.param(18, 2, 9, id="whole_result"),
    pytest.param(8, -2, -4, id="negative_result"),
]


@pytest.mark.xdist_group("add")
def test_add():
    assert add(10, 6) == 16


@pytest.mark.xdist_group("subtract")
def test_subtract():
    assert subtract(10, 4) == 6


@pytest.mark.xdist_group("multiply")
def test_multiply():
    assert multiply(10, 5) == 50


@pytest.mark.xdist_group("divide")
def test_divide():
    assert divide(10, 5) == 2


@pytest.mark.xdist_group("divide")
def test_divide_by_zero_raises_value_error():
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        divide(10, 0)


@pytest.mark.xdist_group("add")
@pytest.mark.parametrize(("value_1", "value_2", "expected"), ADD_CASES)
def test_calculate_add_cases(value_1, value_2, expected):
    assert calculate(value_1, value_2, "add") == expected


@pytest.mark.xdist_group("subtract")
@pytest.mark.parametrize(("value_1", "value_2", "expected"), SUBTRACT_CASES)
def test_calculate_subtract_cases(value_1, value_2, expected):
    assert calculate(value_1, value_2, "subtract") == expected


@pytest.mark.xdist_group("multiply")
@pytest.mark.parametrize(("value_1", "value_2", "expected"), MULTIPLY_CASES)
def test_calculate_multiply_cases(value_1, value_2, expected):
    assert calculate(value_1, value_2, "multiply") == expected


@pytest.mark.xdist_group("divide")
@pytest.mark.parametrize(("value_1", "value_2", "expected"), DIVIDE_CASES)
def test_calculate_divide_cases(value_1, value_2, expected):
    assert calculate(value_1, value_2, "divide") == expected


@pytest.mark.xdist_group("misc")
def test_calculate_with_invalid_operation():
    with pytest.raises(ValueError, match="Unsupported operation: power"):
        calculate(2, 3, "power")


@pytest.mark.xdist_group("misc")
def test_calculator_class_wrapper():
    assert Calculator.multiply(4, 3) == 12
