"""Shared semantic bounds for the current integer Cartesian construction."""

from __future__ import annotations


COORDINATE_MIN = -10
COORDINATE_MAX = 10


def is_coordinate(value: object) -> bool:
    """Return whether value is an exact supported integer coordinate."""

    return type(value) is int and COORDINATE_MIN <= value <= COORDINATE_MAX


def is_exact_coordinate_range(minimum: object, maximum: object) -> bool:
    """Return whether an axis declares the one current production plane."""

    return minimum == COORDINATE_MIN and maximum == COORDINATE_MAX
