"""Analyse d'un dossier : actes -> texte balisé -> LLM -> garde-fous -> base."""
import hashlib
import json
import traceback

from . import db
from .extract import tagged_text
from .llm import LLMIndisponible, generer_fiche
from .schema import Acte, Fiche
from .verify import post_traiter


def construire_texte(docs: list[dict]) -> str:
    return "\n\n".join(tagged_text(d["label"], d["pages"]) for d in docs)


def fiche_pour(docs: list[dict]) -> Fiche:
    """Génère la fiche (ou la reprend du cache si le LLM est indisponible)."""
    texte = construire_texte(docs)
    cache = db.CACHE_DIR / f"{hashlib.sha256(texte.encode()).hexdigest()[:24]}.json"
    try:
        fiche = generer_fiche(texte)
        cache.write_text(fiche.model_dump_json(indent=2), encoding="utf-8")
    except LLMIndisponible as e:
        if not cache.exists():
            raise LLMIndisponible(f"{e} — et aucune fiche en cache pour ces actes.") from e
        fiche = Fiche.model_validate(json.loads(cache.read_text(encoding="utf-8")))

    pages_par_doc = {d["label"]: d["pages"] for d in docs}
    fiche = post_traiter(fiche, pages_par_doc)

    # Rattache chaque acte à son fichier ; ajoute les actes oubliés par le modèle
    par_label = {a.doc: a for a in fiche.actes}
    for d in docs:
        acte = par_label.get(d["label"]) or Acte(doc=d["label"], type_acte="acte (type non identifié)")
        acte.document_id, acte.nb_pages = d["id"], len(d["pages"])
        if not acte.intitule:
            acte.intitule = d["filename"]
        par_label[d["label"]] = acte
    fiche.actes = [par_label[k] for k in sorted(par_label)]
    return fiche


def analyser(dossier_id: int) -> None:
    db.set_statut(dossier_id, "analyse en cours")
    try:
        fiche = fiche_pour(db.documents(dossier_id))
        db.set_statut(dossier_id, "brouillon IA", fiche=fiche.model_dump())
    except Exception as e:
        traceback.print_exc()
        db.set_statut(dossier_id, "erreur", erreur=str(e)[:1000])
