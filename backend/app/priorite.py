"""Priorisation sur critères PROCÉDURAUX OBJECTIFS uniquement, chacun expliqué.

Ordre : 1) urgence invoquée par une partie, 2) échéance la plus proche, 3) ancienneté du dossier.
Jamais de critère tiré du fond ou des chances de succès.
"""
from datetime import date


def _parse(d: str | None) -> date | None:
    try:
        return date.fromisoformat(d[:10]) if d else None
    except ValueError:
        return None


def criteres(fiche: dict | None, aujourd_hui: date | None = None) -> dict:
    aujourd_hui = aujourd_hui or date.today()
    if not fiche:
        return {"cle": (2, 99999, 0), "motifs": []}
    motifs = []

    urgence = bool(fiche.get("urgence_declaree"))
    if urgence:
        motifs.append("Urgence invoquée par une partie")

    ech = fiche.get("prochaine_echeance") or {}
    d_ech = _parse(ech.get("date"))
    jours = (d_ech - aujourd_hui).days if d_ech else None
    if jours is not None:
        quand = f"dans {jours} j" if jours >= 0 else f"dépassée de {-jours} j"
        motifs.append(f"Échéance {quand} ({ech.get('objet', '')})")

    d_intro = _parse((fiche.get("identification") or {}).get("date_introduction"))
    anciennete = (aujourd_hui - d_intro).days if d_intro else 0
    if d_intro:
        motifs.append(f"Introduit il y a {anciennete // 30} mois")

    cle = (0 if urgence else 1, jours if jours is not None else 99999, -anciennete)
    return {"cle": cle, "motifs": motifs, "jours_avant_echeance": jours}
