from __future__ import annotations

import pytest

from pywpdoc import Mm, DocumentValueError
from pywpdoc.core.drawing import (
    CropSpec,
    DrawingLayout,
    DrawingTransform,
    FloatingPlacement,
    HorizontalAlign,
    HorizontalPosition,
    HorizontalRelativeTo,
    InlinePlacement,
    VerticalPosition,
    VerticalRelativeTo,
    WrapMode,
    WrapSide,
    WrapSpec,
)


def test_inline_and_floating_are_one_common_layout_model() -> None:
    inline = DrawingLayout()
    assert isinstance(inline.placement, InlinePlacement)
    assert inline.placement.mode == "inline"

    floating = DrawingLayout(
        placement=FloatingPlacement(
            horizontal=HorizontalPosition(
                relative_to=HorizontalRelativeTo.MARGIN,
                offset=Mm(10),
            ),
            vertical=VerticalPosition(
                relative_to=VerticalRelativeTo.PARAGRAPH,
                offset=Mm(3),
            ),
            wrap=WrapSpec(
                mode=WrapMode.SQUARE,
                side=WrapSide.BOTH,
                distance_left=Mm(1),
                distance_right=Mm(1),
            ),
            behind_text=False,
            allow_overlap=True,
            z_order=2,
        ),
        transform=DrawingTransform(
            rotation_degrees=370,
            crop=CropSpec(left=0.05, right=0.05),
        ),
    )
    assert floating.placement.mode == "floating"
    assert floating.placement.horizontal.offset.mm == pytest.approx(10, abs=0.01)
    assert floating.transform.rotation_degrees == pytest.approx(10)
    assert floating.transform.crop.left == pytest.approx(0.05)


def test_axis_position_uses_align_or_offset_not_both() -> None:
    with pytest.raises(DocumentValueError) as excinfo:
        HorizontalPosition(
            relative_to=HorizontalRelativeTo.PAGE,
            offset=Mm(2),
            align=HorizontalAlign.CENTER,
        )
    assert excinfo.value.code == "drawing-position-conflict"


def test_crop_validation_is_backend_neutral() -> None:
    with pytest.raises(DocumentValueError) as excinfo:
        CropSpec(left=0.7, right=0.4)
    assert excinfo.value.code == "drawing-crop-empty"
