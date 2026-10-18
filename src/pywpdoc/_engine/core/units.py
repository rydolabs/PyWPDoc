from __future__ import annotations


class Length(int):
    """Backend-neutral public length value stored in HWPUNIT internally.

    The integer representation remains HWPUNIT (7200/inch) for backwards
    compatibility with the HWPX engine. Backend adapters must translate the
    physical value rather than assuming the integer unit is native to them.
    """

    @property
    def pt(self) -> float:
        return int(self) / 100.0

    @property
    def mm(self) -> float:
        return int(self) * 25.4 / 7200.0

    @property
    def cm(self) -> float:
        return self.mm / 10.0

    @property
    def inches(self) -> float:
        return int(self) / 7200.0


class Pt(Length):
    def __new__(cls, points: float | int):
        return int.__new__(cls, round(float(points) * 100))


class Mm(Length):
    def __new__(cls, millimeters: float | int):
        return int.__new__(cls, round(float(millimeters) * 7200 / 25.4))


class HwpUnit(Length):
    def __new__(cls, value: int | float):
        return int.__new__(cls, round(float(value)))


class Cm(Length):
    def __new__(cls, centimeters: float | int):
        return int.__new__(cls, round(float(centimeters) * 7200 / 2.54))


class Inches(Length):
    def __new__(cls, inches: float | int):
        return int.__new__(cls, round(float(inches) * 7200))


__all__ = ["Length", "Pt", "Mm", "HwpUnit", "Cm", "Inches"]
