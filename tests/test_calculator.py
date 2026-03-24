import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from calculator import add, subtract, multiply, divide
import pytest


def test_addition():
    assert add(2, 3) == 5
    assert add(0, 0) == 0
    assert add(-1, 1) == 0


def test_subtraction():
    assert subtract(5, 3) == 2
    assert subtract(0, 0) == 0


def test_multiplication():
    assert multiply(3, 4) == 12
    assert multiply(0, 5) == 0


def test_division():
    assert divide(10, 2) == 5.0
    assert divide(0, 5) == 0.0


def test_division_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(5, 0)
