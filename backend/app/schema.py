"""Schéma de la fiche de synthèse MagistrIA.

Ordre des sections = ordre décidé par les magistrats de l'équipe.
Tout élément de contenu porte ses sources (acte, page, paragraphe, extrait littéral).
"""
from typing import Literal

from pydantic import BaseModel, Field

Cote = Literal["demandeur", "defendeur"]


class Source(BaseModel):
    doc: str = Field(description="Lettre de l'acte (A, B, C…)")
    page: int
    paragraphe: str | None = None
    extrait: str = Field("", description="Citation littérale courte (≤ 20 mots)")
    # Rempli par verify.py, jamais par le LLM
    verifie: bool | None = None


class Sourced(BaseModel):
    sources: list[Source] = []


class Acte(BaseModel):
    doc: str
    type_acte: str = Field(description="assignation, conclusions, conclusions récapitulatives…")
    intitule: str = ""
    cote: Cote | None = None
    partie: str = ""
    numero: int | None = None
    recapitulatives: bool = False
    date: str | None = None
    # Rempli par le backend
    document_id: int | None = None
    nb_pages: int | None = None


class Partie(BaseModel):
    nom: str
    cote: Cote
    qualite: str = ""
    avocat: str = ""
    barreau: str = ""


class Identification(BaseModel):
    rg: str | None = None
    juridiction: str | None = None
    chambre: str | None = None
    nature_affaire: str | None = None
    date_introduction: str | None = None
    parties: list[Partie] = []


class Evenement(Sourced):
    date: str | None = None
    description: str


class Position(Sourced):
    texte: str


class FaitConteste(BaseModel):
    objet: str
    demandeur: Position | None = None
    defendeur: Position | None = None


class Moyen(Sourced):
    intitule: str
    expose: str


class Pretention(Sourced):
    texte: str


class TexteCite(Sourced):
    type: Literal["texte", "jurisprudence"]
    reference: str
    cite_par: list[Cote] = []
    url: str | None = None


class Piece(Sourced):
    numero: str
    intitule: str
    cote: Cote | None = None


class Vigilance(Sourced):
    objet: str
    dates_utiles: list[str] = []
    texte_invoque: str | None = None
    delai: str | None = None


class Echeance(Sourced):
    date: str | None = None
    objet: str


class Fiche(BaseModel):
    actes: list[Acte] = []
    identification: Identification = Identification()
    matiere: str = "Non déterminée"
    mots_cles: list[str] = []
    # Vrai seulement si les deux côtés ont produit un acte (calculé par le backend)
    debat_contradictoire: bool = False
    faits_non_contestes: list[Evenement] = []
    faits_contestes: list[FaitConteste] = []
    frise_procedure: list[Evenement] = []
    moyens_demandeur: list[Moyen] = []
    moyens_defendeur: list[Moyen] = []
    pretentions_demandeur: list[Pretention] = []
    pretentions_defendeur: list[Pretention] = []
    textes_cites: list[TexteCite] = []
    pieces: list[Piece] = []
    vigilance: list[Vigilance] = []
    prochaine_echeance: Echeance | None = None
    urgence_declaree: Position | None = None
    # Rempli par verify.py
    alertes: list[str] = []
