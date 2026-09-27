from types import SimpleNamespace

from app.core.database import (
    _EmptyMaybeSingleResponse,
    _normalize_maybe_single_response,
)


def test_maybe_single_zero_rows_keeps_response_data_contract():
    response = _normalize_maybe_single_response(None)

    assert isinstance(response, _EmptyMaybeSingleResponse)
    assert response.data is None
    assert response.count is None


def test_maybe_single_existing_row_is_unchanged():
    response = SimpleNamespace(data={"id": "member-1"}, count=1)

    assert _normalize_maybe_single_response(response) is response
