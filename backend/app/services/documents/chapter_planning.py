"""Turns AI-detected chapters into a consistent, page-accurate chapter list."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.ai.schemas import DetectedChapter

FALLBACK_CHAPTER_TITLE = "Wortschatz"
MAX_TITLE_LENGTH = 255


@dataclass(frozen=True, slots=True)
class PlannedChapter:
    title: str
    chapter_number: int | None
    order: int
    start_page: int
    end_page: int


def plan_chapters(detected: Sequence[DetectedChapter], page_count: int) -> list[PlannedChapter]:
    """Validate, order and de-duplicate chapters and compute their page ranges.

    - Chapters outside the document's pages and repeated chapter numbers are dropped
      (the first occurrence wins, e.g. for running headers reported on every page).
    - A chapter ends on the page before the next chapter starts, or on that same page
      when the next chapter starts mid-page (the page is then shared).
    - A document without detectable chapters becomes one chapter spanning all pages.
    """
    heads: list[DetectedChapter] = []
    seen_numbers: set[int] = set()
    for chapter in sorted(detected, key=lambda c: c.start_page):
        if not 1 <= chapter.start_page <= page_count:
            continue
        number = chapter.chapter_number
        if number is not None:
            if number in seen_numbers:
                continue
            seen_numbers.add(number)
        title = " ".join(chapter.title.split()) or (f"Kapitel {number}" if number else "")
        if title:
            heads.append(chapter.model_copy(update={"title": title[:MAX_TITLE_LENGTH]}))

    if not heads:
        heads = [DetectedChapter(title=FALLBACK_CHAPTER_TITLE, chapter_number=None, start_page=1)]

    planned = []
    for index, head in enumerate(heads):
        if index + 1 < len(heads):
            following = heads[index + 1]
            end = following.start_page if following.starts_mid_page else following.start_page - 1
        else:
            end = page_count
        planned.append(
            PlannedChapter(
                title=head.title,
                chapter_number=head.chapter_number,
                order=index + 1,
                start_page=head.start_page,
                end_page=max(head.start_page, end),
            )
        )
    return planned
