"""Garde-fous appliqués APRÈS le LLM :
- chaque extrait cité doit exister dans le texte de l'acte, à la page indiquée (ou voisine) ;
- aucun vocabulaire décisionnel dans les sections rédigées par l'outil ;
- liens Légifrance construits pour les textes cités.
"""
import re
import unicodedata
from urllib.parse import quote_plus

from .schema import Evenement, Fiche, Source

# Mots interdits dans les sections où l'outil parle en son nom propre
# (dans les moyens, les parties peuvent évidemment soutenir qu'une demande est irrecevable).
TERMES_DECISIONNELS = [
    "prescrit", "prescrite", "forclos", "forclose", "irrecevable", "recevable",
    "bien fondé", "bien fondée", "mal fondé", "mal fondée", "infondé", "infondée",
    "à tort", "à juste titre", "manifestement", "incontestablement",
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _trouve(extrait: str, page_text: str) -> bool:
    e, p = _norm(extrait), _norm(page_text)
    if not e:
        return False
    if e in p:
        return True
    # Tolérance (coupures de ligne, ligatures, petites reformulations) : 85 % des mots présents
    mots = e.split()
    pset = set(p.split())
    return len(mots) >= 4 and sum(m in pset for m in mots) / len(mots) >= 0.85


def _verifier_source(src: Source, pages_par_doc: dict[str, list[str]]) -> None:
    pages = pages_par_doc.get(src.doc)
    if not pages:
        src.verifie = False
        return
    # Page indiquée d'abord, puis pages voisines (citation à cheval sur deux pages)
    for p in [src.page, src.page - 1, src.page + 1]:
        if 1 <= p <= len(pages) and _trouve(src.extrait, pages[p - 1]):
            src.page = p
            src.verifie = True
            return
    src.verifie = False


def _iter_sources(obj):
    if isinstance(obj, Source):
        yield obj
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_sources(x)
    elif hasattr(obj, "__dict__") and hasattr(obj, "model_fields"):
        for name in type(obj).model_fields:
            yield from _iter_sources(getattr(obj, name))


def url_legifrance(reference: str, type_: str) -> str:
    onglet = "juri" if type_ == "jurisprudence" else "code"
    return f"https://www.legifrance.gouv.fr/search/{onglet}?tab_selection={onglet}&query={quote_plus(reference)}"


def post_traiter(fiche: Fiche, pages_par_doc: dict[str, list[str]]) -> Fiche:
    alertes: list[str] = []

    # 1. Sources
    sources = list(_iter_sources(fiche))
    for s in sources:
        _verifier_source(s, pages_par_doc)
    non_verifiees = [s for s in sources if not s.verifie]
    if non_verifiees:
        alertes.append(
            f"{len(non_verifiees)} source(s) sur {len(sources)} n'ont pas pu être retrouvées mot pour mot "
            "dans les actes : elles sont signalées ⚠ et doivent être contrôlées."
        )

    # 2. Contradictoire réel seulement si les deux côtés ont produit un acte
    cotes = {a.cote for a in fiche.actes if a.cote}
    fiche.debat_contradictoire = cotes == {"demandeur", "defendeur"}
    if not fiche.debat_contradictoire and fiche.faits_contestes:
        # Sans acte en réponse, rien n'est encore « contesté » : on reverse dans les faits allégués
        for fc in fiche.faits_contestes:
            for pos in (fc.demandeur, fc.defendeur):
                if pos:
                    fiche.faits_non_contestes.append(Evenement(description=pos.texte, sources=pos.sources))
        fiche.faits_contestes = []

    # 3. Vocabulaire décisionnel dans les sections rédigées par l'outil
    textes_outil = [v.objet for v in fiche.vigilance] + [v.delai or "" for v in fiche.vigilance]
    textes_outil += [f.objet for f in fiche.faits_contestes]
    textes_outil += [e.description for e in fiche.faits_non_contestes]
    for t in textes_outil:
        nt = f" {_norm(t)} "
        for terme in TERMES_DECISIONNELS:
            if f" {_norm(terme)} " in nt:
                alertes.append(f"Formulation à relire (vocabulaire décisionnel « {terme} ») : « {t[:120]} »")
                break

    # 4. Liens Légifrance
    for t in fiche.textes_cites:
        t.url = url_legifrance(t.reference, t.type)

    fiche.alertes = alertes
    return fiche
