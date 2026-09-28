import pymupdf


def make_pdf(pages: list[str], *, password: str | None = None) -> bytes:
    """Build an in-memory PDF with one page per string (empty string → blank page)."""
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text, fontsize=11)
    if password is None:
        data = document.tobytes()
    else:
        data = document.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password
        )
    document.close()
    return data
