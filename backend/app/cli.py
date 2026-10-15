"""Test en ligne de commande, sans base ni interface :

    python -m app.cli ../samples/assignation.pdf ../samples/conclusions.pdf
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from .extract import extract_pages  # noqa: E402
from .pipeline import fiche_pour  # noqa: E402


def main(paths: list[str]) -> None:
    docs = [
        {"id": None, "label": chr(ord("A") + i), "filename": Path(p).name, "pages": extract_pages(p)}
        for i, p in enumerate(paths)
    ]
    for d in docs:
        print(f"Acte {d['label']} : {d['filename']} ({len(d['pages'])} pages)", file=sys.stderr)
    fiche = fiche_pour(docs)
    print(fiche.model_dump_json(indent=2))
    sources = [s for s in _all_sources(fiche.model_dump())]
    ok = sum(1 for s in sources if s.get("verifie"))
    print(f"\nSources vérifiées : {ok}/{len(sources)}", file=sys.stderr)
    for a in fiche.alertes:
        print(f"⚠ {a}", file=sys.stderr)


def _all_sources(obj):
    if isinstance(obj, dict):
        if {"doc", "page", "extrait"} <= obj.keys():
            yield obj
        for v in obj.values():
            yield from _all_sources(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_sources(v)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
