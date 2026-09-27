import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.annotations import AnnotationCreate, Rectangle


def test_rectangle_accepts_normalized_coordinates():
    rect = Rectangle(x=0.1, y=0.2, width=0.3, height=0.4)
    assert rect.x == 0.1
    assert rect.y == 0.2
    assert rect.width == 0.3
    assert rect.height == 0.4


def test_rectangle_rejects_overflow():
    with pytest.raises(ValidationError):
        Rectangle(x=0.8, y=0.2, width=0.3, height=0.4)

    with pytest.raises(ValidationError):
        Rectangle(x=0.2, y=0.8, width=0.3, height=0.3)


def test_annotation_normalizes_hex_color():
    payload = AnnotationCreate(
        page_number=1,
        annotation_type="rectangle",
        rectangles=[Rectangle(x=0.1, y=0.1, width=0.2, height=0.2)],
        color="#f4d06f",
    )
    assert payload.color == "#F4D06F"


def test_annotation_rejects_invalid_color():
    with pytest.raises(ValidationError):
        AnnotationCreate(
            page_number=1,
            rectangles=[Rectangle(x=0.1, y=0.1, width=0.2, height=0.2)],
            color="yellow",
        )
