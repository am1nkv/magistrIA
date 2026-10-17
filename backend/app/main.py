"""API MagistrIA."""
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402

from . import db  # noqa: E402
from .extract import extract_pages  # noqa: E402
from .export_pdf import synthese_pdf  # noqa: E402
from .llm import llm_configure, nom_modele, ollama_modeles, provider  # noqa: E402
from .pipeline import analyser  # noqa: E402
from .priorite import criteres  # noqa: E402

db.init()
app = FastAPI(title="MagistrIA")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/status")
def status():
    return {"llm": llm_configure(), "mode": os.getenv("MAGISTRIA_MODE") or "normal",
            "fournisseur": provider(), "modele": nom_modele(),
            "ollama_modeles": ollama_modeles() if provider() == "ollama" else []}


async def _enregistrer(dossier_id: int, files: list[UploadFile]) -> None:
    for f in files:
        contenu = await f.read()
        if not contenu.startswith(b"%PDF"):
            raise HTTPException(400, f"{f.filename} n'est pas un PDF")
        path = db.UPLOAD_DIR / f"{uuid.uuid4().hex}.pdf"
        path.write_bytes(contenu)
        db.add_document(dossier_id, f.filename or path.name, str(path), extract_pages(str(path)))


@app.post("/api/dossiers")
async def creer_dossier(files: list[UploadFile], background: BackgroundTasks):
    dossier_id = db.create_dossier()
    try:
        await _enregistrer(dossier_id, files)
    except Exception:
        db.delete_dossier(dossier_id)
        raise
    background.add_task(analyser, dossier_id)
    return {"id": dossier_id}


@app.post("/api/dossiers/{dossier_id}/actes")
async def ajouter_actes(dossier_id: int, files: list[UploadFile], background: BackgroundTasks):
    d = db.dossier(dossier_id)
    if not d:
        raise HTTPException(404)
    if d["fictif"]:
        raise HTTPException(400, "Dossier fictif de démonstration : ajout d'actes impossible")
    await _enregistrer(dossier_id, files)
    db.set_statut(dossier_id, "analyse en cours")
    background.add_task(analyser, dossier_id)
    return {"id": dossier_id}


@app.post("/api/dossiers/{dossier_id}/relancer")
def relancer(dossier_id: int, background: BackgroundTasks):
    d = db.dossier(dossier_id)
    if not d or d["fictif"]:
        raise HTTPException(404)
    db.set_statut(dossier_id, "analyse en cours")
    background.add_task(analyser, dossier_id)
    return {"id": dossier_id}


def _resume(d: dict) -> dict:
    f = d["fiche"] or {}
    ident = f.get("identification") or {}
    prio = criteres(f if d["statut"] != "analyse en cours" else None)
    return {
        "id": d["id"],
        "statut": d["statut"],
        "erreur": d["erreur"],
        "fictif": d["fictif"],
        "created_at": d["created_at"],
        "rg": ident.get("rg"),
        "juridiction": ident.get("juridiction"),
        "parties": {
            c: [p["nom"] for p in ident.get("parties", []) if p.get("cote") == c] for c in ("demandeur", "defendeur")
        },
        "nature_affaire": ident.get("nature_affaire"),
        "matiere": f.get("matiere"),
        "mots_cles": f.get("mots_cles", []),
        "articles": [t["reference"] for t in f.get("textes_cites", []) if t.get("type") == "texte"],
        "date_introduction": ident.get("date_introduction"),
        "prochaine_echeance": f.get("prochaine_echeance"),
        "nb_actes": len(f.get("actes", [])),
        "priorite_cle": list(prio["cle"]),
        "priorite_motifs": prio["motifs"],
    }


@app.get("/api/dossiers")
def lister():
    resumes = [_resume(d) for d in db.dossiers()]
    resumes.sort(key=lambda r: r["priorite_cle"])
    for i, r in enumerate(resumes, start=1):
        r["priorite_rang"] = i
    return resumes


@app.get("/api/dossiers/{dossier_id}")
def detail(dossier_id: int):
    d = db.dossier(dossier_id)
    if not d:
        raise HTTPException(404)
    docs = [{"id": x["id"], "label": x["label"], "filename": x["filename"], "nb_pages": len(x["pages"])}
            for x in db.documents(dossier_id)]
    return {**d, "documents": docs, "resume": _resume(d), "similaires": _similaires(d)}


def _similaires(d: dict) -> list[dict]:
    """Version MVP : même matière ou au moins 2 mots-clés communs (la vraie similarité est « à terme »)."""
    f = d["fiche"] or {}
    mots = {m.lower() for m in f.get("mots_cles", [])}
    out = []
    for autre in db.dossiers():
        g = autre["fiche"]
        if autre["id"] == d["id"] or not g:
            continue
        communs = sorted(mots & {m.lower() for m in g.get("mots_cles", [])})
        meme_matiere = f.get("matiere") and g.get("matiere") == f.get("matiere")
        if meme_matiere or len(communs) >= 2:
            raisons = (["même matière"] if meme_matiere else []) + ([f"mots-clés : {', '.join(communs)}"] if communs else [])
            out.append({"id": autre["id"], "rg": (g.get("identification") or {}).get("rg"),
                        "nature_affaire": (g.get("identification") or {}).get("nature_affaire"),
                        "raisons": raisons})
    return out[:5]


@app.delete("/api/dossiers/{dossier_id}")
def supprimer(dossier_id: int):
    db.delete_dossier(dossier_id)
    return {"ok": True}


@app.get("/api/files/{doc_id}")
def fichier(doc_id: int):
    doc = db.document(doc_id)
    if not doc:
        raise HTTPException(404)
    return FileResponse(doc["path"], media_type="application/pdf",
                        filename=doc["filename"], content_disposition_type="inline")


@app.get("/api/dossiers/{dossier_id}/synthese.pdf")
def synthese(dossier_id: int):
    """Fiche de synthèse standardisée, 4 pages A4 maximum."""
    d = db.dossier(dossier_id)
    if not d or not d["fiche"]:
        raise HTTPException(404, "Aucune fiche disponible pour ce dossier")
    pdf = synthese_pdf(d["fiche"])
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="synthese-dossier-{dossier_id}.pdf"'})
