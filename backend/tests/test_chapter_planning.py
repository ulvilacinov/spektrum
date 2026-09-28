from app.services.documents.chapter_planning import PlannedChapter, plan_chapters
from tests.fake_ai import chapter


def spans(planned: list[PlannedChapter]) -> list[tuple[str, int, int, int]]:
    return [(c.title, c.order, c.start_page, c.end_page) for c in planned]


def test_chapter_ends_on_the_page_before_the_next_chapter() -> None:
    planned = plan_chapters([chapter(2, 4), chapter(1, 2)], page_count=5)

    assert spans(planned) == [("Kapitel 1", 1, 2, 3), ("Kapitel 2", 2, 4, 5)]
    assert [c.chapter_number for c in planned] == [1, 2]


def test_page_is_shared_when_next_chapter_starts_mid_page() -> None:
    planned = plan_chapters(
        [chapter(1, 1), chapter(2, 2).model_copy(update={"starts_mid_page": True})], page_count=3
    )

    assert spans(planned) == [("Kapitel 1", 1, 1, 2), ("Kapitel 2", 2, 2, 3)]


def test_titles_are_whitespace_normalized() -> None:
    planned = plan_chapters([chapter(2, 1, title="Kapitel  2:\n Arbeit")], page_count=1)

    assert planned[0].title == "Kapitel 2: Arbeit"


def test_running_headers_reported_on_every_page_keep_the_first_page() -> None:
    detected = [chapter(1, 1), chapter(1, 2), chapter(2, 3), chapter(2, 4), chapter(3, 5)]

    planned = plan_chapters(detected, page_count=6)

    assert spans(planned) == [
        ("Kapitel 1", 1, 1, 2),
        ("Kapitel 2", 2, 3, 4),
        ("Kapitel 3", 3, 5, 6),
    ]


def test_drops_chapters_outside_the_document() -> None:
    planned = plan_chapters([chapter(1, 1), chapter(2, 3), chapter(3, 9), chapter(4, 0)], 3)

    assert spans(planned) == [("Kapitel 1", 1, 1, 2), ("Kapitel 2", 2, 3, 3)]


def test_unnumbered_sections_are_kept() -> None:
    planned = plan_chapters([chapter(None, 1, title="Einleitung"), chapter(1, 2)], page_count=2)

    assert [(c.title, c.chapter_number) for c in planned] == [
        ("Einleitung", None),
        ("Kapitel 1", 1),
    ]


def test_blank_title_falls_back_to_chapter_number() -> None:
    planned = plan_chapters([chapter(3, 1, title="   ")], page_count=1)

    assert planned[0].title == "Kapitel 3"


def test_without_chapters_the_whole_document_is_one_chapter() -> None:
    planned = plan_chapters([], page_count=3)

    assert spans(planned) == [("Wortschatz", 1, 1, 3)]
    assert planned[0].chapter_number is None
