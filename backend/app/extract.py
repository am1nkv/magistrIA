"""Extraction du texte des PDF, page par page, pour pouvoir citer « p. N, § M »."""
import pymupdf


def extract_pages(path: str) -> list[str]:
    """Texte de chaque page (index 0 = page 1)."""
    with pymupdf.open(path) as pdf:
        return [page.get_text("text") for page in pdf]


def tagged_text(label: str, pages: list[str]) -> str:
    """Texte balisé envoyé au LLM : chaque page est précédée de son repère."""
    parts = []
    for i, text in enumerate(pages, start=1):
        parts.append(f"<<<ACTE {label} | PAGE {i}>>>\n{text.strip()}")
    return "\n\n".join(parts)
