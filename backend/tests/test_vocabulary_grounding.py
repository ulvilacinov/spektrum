from app.domain.entities import ExtractedPage
from app.services.ai.schemas import ExtractedVocabularyItem
from app.services.documents.vocabulary_grounding import ground_items
from tests.fake_ai import vocab

PAGES = [
    ExtractedPage(page_number=3, text="Kapitel 1\ndie Veranstaltung   etkinlik\nim Stau stehen"),
    ExtractedPage(page_number=4, text="an einer Konfe-\nrenz teilnehmen\n„Das ist mir egal“"),
]


def test_accepts_items_found_on_their_page() -> None:
    result = ground_items([vocab("die Veranstaltung", "etkinlik", 3)], PAGES)

    assert [(i.german, i.source_page) for i in result.accepted] == [("die Veranstaltung", 3)]
    assert result.rejected == []


def test_rejects_invented_vocabulary() -> None:
    result = ground_items([vocab("der Flughafen", "havalimanı", 3)], PAGES)

    assert result.accepted == []
    assert [r.reason for r in result.rejected] == ["not found in the source pages"]


def test_corrects_a_wrong_source_page() -> None:
    result = ground_items([vocab("im Stau stehen", "trafikte kalmak", 4)], PAGES)

    assert result.accepted[0].source_page == 3


def test_matching_ignores_case_whitespace_quotes_and_hyphenation() -> None:
    items = [
        vocab("die Veranstaltung", "etkinlik", 3, source_text="DIE  Veranstaltung,"),
        vocab("an einer Konferenz teilnehmen", "bir konferansa katılmak", 4),
        vocab("Das ist mir egal", "umurumda değil", 4, source_text='"Das ist mir egal"'),
    ]

    result = ground_items(items, PAGES)

    assert result.rejected == []
    assert len(result.accepted) == 3


def test_falls_back_to_german_when_source_text_is_missing() -> None:
    result = ground_items([vocab("im Stau stehen", "trafikte kalmak", 3, source_text=None)], PAGES)

    assert result.accepted[0].source_text == "im Stau stehen"


def test_rejects_items_without_required_fields() -> None:
    items = [
        ExtractedVocabularyItem(german="im Stau stehen", turkish="  ", source_page=3),
        ExtractedVocabularyItem(german=None, turkish="etkinlik", source_page=3),
    ]

    result = ground_items(items, PAGES)

    assert [r.reason for r in result.rejected] == [
        "missing Turkish meaning",
        "missing German text",
    ]


def test_drops_optional_values_that_do_not_fit_their_column() -> None:
    item = vocab("die Veranstaltung", "etkinlik", 3, article="die " * 10, base_verb=None)

    accepted = ground_items([item], PAGES).accepted[0]

    assert accepted.article is None
    assert accepted.german == "die Veranstaltung"


def test_unknown_item_type_falls_back_to_word() -> None:
    item = ExtractedVocabularyItem.model_validate(
        {"german": "egal", "turkish": "fark etmez", "item_type": "adjective"}
    )

    assert item.item_type == "word"


def test_symbol_font_bullets_are_ignored() -> None:
    bullet = ""  # Wingdings bullet as extracted from real PDFs
    pages = [
        ExtractedPage(page_number=1, text=f"{bullet}\tim Stau stehen\n{bullet}\tWäsche waschen")
    ]
    items = [
        vocab("im Stau stehen", "trafikte kalmak", 1),
        vocab("Wäsche waschen", "çamaşır yıkamak", 1, source_text=f"{bullet} Wäsche waschen"),
    ]

    assert len(ground_items(items, pages).accepted) == 2


def test_entries_wrapped_across_lines_as_in_real_pdfs() -> None:
    soft_hyphen = "­"
    pages = [
        ExtractedPage(
            page_number=20,
            text=(
                f"Nachrichtenredakteur/in: Material aus Agentur{soft_hyphen}\n"
                "meldungen auswerten/bearbeiten\n"
                "Mich interessiert am meisten (das Albrecht-Dürer-\nHaus).\n"
                "Das Interesse an (persönlichen Treffen) steigt/sinkt/\ngeht zurück."
            ),
        )
    ]
    items = [
        vocab("Material aus Agenturmeldungen auswerten/bearbeiten", "haber ajansı materyali", 20),
        vocab("Mich interessiert am meisten (das Albrecht-Dürer-Haus).", "en çok ilgimi…", 20),
        vocab(
            "Das Interesse an (persönlichen Treffen) steigt/sinkt/geht zurück.", "ilgi artar", 20
        ),
    ]

    result = ground_items(items, pages)

    assert result.rejected == []
