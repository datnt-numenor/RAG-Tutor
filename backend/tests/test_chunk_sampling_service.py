from app.services.chunk_sampling_service import (
    interleave_groups,
    sample_evenly,
)


def rows(count: int) -> list[dict]:
    return [{"chunk_index": index} for index in range(count)]


def test_sample_evenly_covers_beginning_middle_and_end():
    sampled = sample_evenly(rows(10), 4)
    indexes = [item["chunk_index"] for item in sampled]

    assert len(indexes) == 4
    assert indexes[0] == 0
    assert indexes[-1] == 9
    assert len(set(indexes)) == 4


def test_sample_evenly_returns_all_when_under_limit():
    source = rows(3)
    assert sample_evenly(source, 5) == source


def test_interleave_groups_round_robins_documents():
    result = interleave_groups(
        [
            [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}],
            [{"id": "b1"}, {"id": "b2"}],
            [{"id": "c1"}],
        ],
        6,
    )
    assert [item["id"] for item in result] == [
        "a1",
        "b1",
        "c1",
        "a2",
        "b2",
        "a3",
    ]


def test_interleave_respects_limit():
    result = interleave_groups(
        [
            [{"id": "a1"}, {"id": "a2"}],
            [{"id": "b1"}, {"id": "b2"}],
        ],
        3,
    )
    assert [item["id"] for item in result] == ["a1", "b1", "a2"]
