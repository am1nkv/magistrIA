"""Stockage SQLite (local, jamais commité : backend/data/)."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "magistria.db"

for d in (DATA_DIR, UPLOAD_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with connect() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                statut TEXT NOT NULL,          -- 'analyse en cours' | 'brouillon IA' | 'erreur'
                erreur TEXT,
                fiche TEXT,                    -- JSON de la fiche
                fictif INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dossier_id INTEGER NOT NULL REFERENCES dossiers(id) ON DELETE CASCADE,
                label TEXT NOT NULL,           -- A, B, C…
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                pages TEXT NOT NULL,           -- JSON : texte par page
                uploaded_at TEXT NOT NULL
            );
            """
        )


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_dossier(fictif: bool = False, fiche: dict | None = None) -> int:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO dossiers (created_at, updated_at, statut, fiche, fictif) VALUES (?, ?, ?, ?, ?)",
            (now(), now(), "brouillon IA" if fiche else "analyse en cours",
             json.dumps(fiche, ensure_ascii=False) if fiche else None, int(fictif)),
        )
        return cur.lastrowid


def add_document(dossier_id: int, filename: str, path: str, pages: list[str]) -> dict:
    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM documents WHERE dossier_id = ?", (dossier_id,)).fetchone()[0]
        label = chr(ord("A") + n)
        cur = c.execute(
            "INSERT INTO documents (dossier_id, label, filename, path, pages, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (dossier_id, label, filename, path, json.dumps(pages, ensure_ascii=False), now()),
        )
        return {"id": cur.lastrowid, "label": label}


def documents(dossier_id: int) -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM documents WHERE dossier_id = ? ORDER BY label", (dossier_id,)).fetchall()
    return [{**dict(r), "pages": json.loads(r["pages"])} for r in rows]


def document(doc_id: int) -> dict | None:
    with connect() as c:
        r = c.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(r) if r else None


def set_statut(dossier_id: int, statut: str, erreur: str | None = None, fiche: dict | None = None) -> None:
    with connect() as c:
        if fiche is not None:
            c.execute(
                "UPDATE dossiers SET statut = ?, erreur = ?, fiche = ?, updated_at = ? WHERE id = ?",
                (statut, erreur, json.dumps(fiche, ensure_ascii=False), now(), dossier_id),
            )
        else:
            c.execute(
                "UPDATE dossiers SET statut = ?, erreur = ?, updated_at = ? WHERE id = ?",
                (statut, erreur, now(), dossier_id),
            )


def dossiers() -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM dossiers ORDER BY id DESC").fetchall()
    return [_row(r) for r in rows]


def dossier(dossier_id: int) -> dict | None:
    with connect() as c:
        r = c.execute("SELECT * FROM dossiers WHERE id = ?", (dossier_id,)).fetchone()
    return _row(r) if r else None


def delete_dossier(dossier_id: int) -> None:
    for d in documents(dossier_id):
        Path(d["path"]).unlink(missing_ok=True)
    with connect() as c:
        c.execute("DELETE FROM documents WHERE dossier_id = ?", (dossier_id,))
        c.execute("DELETE FROM dossiers WHERE id = ?", (dossier_id,))


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["fiche"] = json.loads(d["fiche"]) if d["fiche"] else None
    d["fictif"] = bool(d["fictif"])
    return d
