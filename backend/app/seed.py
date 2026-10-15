"""Ajoute 3 dossiers FICTIFS (marqués comme tels) pour que le tableau de bord de démo ne soit pas vide.

    python -m app.seed          # ajoute
    python -m app.seed --reset  # supprime tous les dossiers fictifs puis les recrée
"""
import sys
from datetime import date, timedelta

from . import db
from .schema import Fiche
from .verify import url_legifrance


def _j(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def _fiche(rg, nature, matiere, mots, dem, defd, intro, ech_j, ech_objet, textes, moyens_dem, moyens_def, urgence=None):
    f = {
        "identification": {
            "rg": rg, "juridiction": "Tribunal judiciaire (fictif)", "chambre": "Chambre civile",
            "nature_affaire": nature, "date_introduction": intro,
            "parties": [{"nom": dem, "cote": "demandeur", "avocat": "Me A. (fictif)"},
                        {"nom": defd, "cote": "defendeur", "avocat": "Me B. (fictif)"}],
        },
        "actes": [{"doc": "A", "type_acte": "assignation", "cote": "demandeur", "partie": dem, "date": intro},
                  {"doc": "B", "type_acte": "conclusions", "cote": "defendeur", "partie": defd, "numero": 1}],
        "matiere": matiere, "mots_cles": mots, "debat_contradictoire": True,
        "frise_procedure": [{"date": intro, "description": "Délivrance de l'assignation"}],
        "moyens_demandeur": [{"intitule": i, "expose": e} for i, e in moyens_dem],
        "moyens_defendeur": [{"intitule": i, "expose": e} for i, e in moyens_def],
        "textes_cites": [{"type": "texte", "reference": r, "cite_par": c, "url": url_legifrance(r, "texte")} for r, c in textes],
        "prochaine_echeance": {"date": _j(ech_j), "objet": ech_objet},
        "urgence_declaree": {"texte": urgence} if urgence else None,
        "alertes": ["Dossier FICTIF de démonstration : aucun acte réel, aucune source."],
    }
    return Fiche.model_validate(f).model_dump()


DOSSIERS = [
    lambda: _fiche("24/00871", "Bail commercial — loyers impayés et clause résolutoire", "Bail",
                   ["bail commercial", "clause résolutoire", "loyers impayés", "commandement de payer"],
                   "SCI Les Tilleuls (fictif)", "SARL Boulangerie du Port (fictif)", "2024-09-12", 9,
                   "Audience de plaidoirie",
                   [("Article L.145-41 du Code de commerce", ["demandeur", "defendeur"])],
                   [("Acquisition de la clause résolutoire", "La SCI soutient que le commandement de payer est resté infructueux plus d'un mois.")],
                   [("Délais de paiement", "La SARL sollicite des délais et la suspension des effets de la clause résolutoire.")]),
    lambda: _fiche("23/04410", "Construction — désordres après réception", "Construction",
                   ["garantie décennale", "réception", "désordres", "expertise"],
                   "M. et Mme D. (fictif)", "Entreprise Bâti-Sud (fictif)", "2023-11-03", 32,
                   "Dépôt du rapport d'expertise",
                   [("Article 1792 du Code civil", ["demandeur"]), ("Article 1792-6 du Code civil", ["defendeur"])],
                   [("Responsabilité décennale", "Les époux D. soutiennent que les fissures rendent l'ouvrage impropre à sa destination.")],
                   [("Absence de réception", "L'entreprise fait valoir qu'aucune réception n'est intervenue.")]),
    lambda: _fiche("25/00112", "Crédit à la consommation — déchéance du terme", "Consommation",
                   ["crédit à la consommation", "déchéance du terme", "forclusion biennale"],
                   "Banque Exemple (fictif)", "Mme L. (fictif)", "2025-01-20", 4,
                   "Date de renvoi — conclusions du demandeur",
                   [("Article R.312-35 du Code de la consommation", ["defendeur"])],
                   [("Exigibilité de la créance", "La banque soutient que la déchéance du terme a été régulièrement prononcée.")],
                   [("Délai biennal", "Mme L. fait valoir que l'action a été engagée plus de deux ans après le premier incident non régularisé.")],
                   urgence="Mme L. invoque une procédure de saisie imminente sur son logement."),
]


def main() -> None:
    db.init()
    if "--reset" in sys.argv:
        for d in db.dossiers():
            if d["fictif"]:
                db.delete_dossier(d["id"])
    for make in DOSSIERS:
        db.create_dossier(fictif=True, fiche=make())
    print(f"{len(DOSSIERS)} dossiers fictifs ajoutés.")


if __name__ == "__main__":
    main()
