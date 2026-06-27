#!/usr/bin/env python3
from __future__ import annotations


def increment(counter: dict[str, int], value: str) -> None:
    if value:
        counter[value] = counter.get(value, 0) + 1
