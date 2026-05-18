from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.types import UserDefinedType


@dataclass(frozen=True, slots=True)
class BBox:
    """Axis-aligned bounding box in image coordinates (y increases downward)."""

    ul_x: int
    ul_y: int
    lr_x: int
    lr_y: int


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


class Box(UserDefinedType):
    """SQLAlchemy adapter for Postgres `box`.

    Postgres reorders the two stored points into a canonical form, so reads
    are normalized back to (ul = min, lr = max) in image coords.
    """

    cache_ok = True

    def get_col_spec(self, **kw) -> str:
        return "box"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if isinstance(value, BBox):
                return f"({value.ul_x},{value.ul_y}),({value.lr_x},{value.lr_y})"
            (x1, y1), (x2, y2) = value
            return f"({x1},{y1}),({x2},{y2})"

        return process

    def bind_expression(self, bindvalue):
        return func.cast(bindvalue, type_=self)

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                nums = [int(float(n)) for n in _NUM_RE.findall(value)]
                if len(nums) != 4:
                    return None
                x1, y1, x2, y2 = nums
                return BBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            return value

        return process
