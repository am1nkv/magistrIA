"""Export de la fiche en PDF standardisé : A4, 4 pages maximum, ordre fixe des sections."""
from html import escape

import io

import pymupdf

MAX_PAGES = 4
TAILLES = (9.5, 9, 8.5, 8, 7.5, 7, 6.5)  # corps de texte (pt), du plus lisible au plus compact
MARGES = (40, 40, -40, -48)  # gauche, haut, droite, bas
BANDEAU = "Synthèse IA — brouillon à valider — pas une analyse du fond"

CSS = """
body { font-family: sans-serif; color: #1a1a1a; }
h1 { font-size: 150%; margin: 0 0 2pt 0; }
h2 { font-size: 112%; margin: 7pt 0 2pt 0; color: #1f3a5f; border-bottom: 0.6pt solid #1f3a5f; }
p, li { margin: 0 0 1.5pt 0; }
ul { margin: 0; padding-left: 10pt; }
.src { color: #666; font-size: 85%; }
.muted { color: #666; }
.ban { color: #8a4b00; font-weight: bold; }
table { width: 100%; border-collapse: collapse; }
td, th { width: 50%; vertical-align: top; padding: 2pt 4pt; border: 0.5pt solid #bbb; }
th { background-color: #e8edf3; text-align: left; }
"""


def _e(x) -> str:
    return escape(str(x)) if x not in (None, "") else ""


def _src(el: dict) -> str:
    parts = []
    for s in (el.get("sources") or [])[:3]:
        t = f"{s.get('doc', '?')} · p. {s.get('page', '?')}"
        if s.get("paragraphe"):
            t += f" · §{s['paragraphe']}"
        parts.append(t)
    return f' <span class="src">({_e("; ".join(parts))})</span>' if parts else ""


def _liste(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else '<p class="muted">Néant</p>'


def _date(d) -> str:
    return f"{_e(d)} — " if d else ""


def _html(f: dict, limite: int | None) -> str:
    """limite : nombre maximal d'éléments par liste (None = tout) — repli si la taille minimale ne suffit pas."""
    def cut(xs):
        return (xs or [])[:limite] if limite else (xs or [])

    ident = f.get("identification") or {}
    parties = ident.get("parties") or []
    h = [f"<h1>Fiche de synthèse — RG {_e(ident.get('rg') or 'n.c.')}</h1>",
         f'<p class="ban">{BANDEAU}</p>']

    # 1. Identification
    h.append("<h2>1. Identification</h2>")
    lignes = [f"<b>Juridiction :</b> {_e(ident.get('juridiction') or 'n.c.')}"
              + (f" — {_e(ident.get('chambre'))}" if ident.get("chambre") else ""),
              f"<b>Nature de l'affaire :</b> {_e(ident.get('nature_affaire') or 'n.c.')} "
              f"(matière : {_e(f.get('matiere'))})",
              f"<b>Date d'introduction :</b> {_e(ident.get('date_introduction') or 'n.c.')}"]
    for c, lib in (("demandeur", "Demandeur"), ("defendeur", "Défendeur")):
        for p in parties:
            if p.get("cote") == c:
                av = f" — {_e(p['avocat'])}" + (f" ({_e(p['barreau'])})" if p.get("barreau") else "") if p.get("avocat") else ""
                lignes.append(f"<b>{lib} :</b> {_e(p.get('nom'))}"
                              + (f", {_e(p['qualite'])}" if p.get("qualite") else "") + av)
    ech = f.get("prochaine_echeance")
    if ech:
        lignes.append(f"<b>Prochaine échéance :</b> {_date(ech.get('date'))}{_e(ech.get('objet'))}{_src(ech)}")
    h.append("".join(f"<p>{x}</p>" for x in lignes))

    # 2. Mots-clés
    h.append("<h2>2. Mots-clés</h2>")
    h.append(f"<p>{_e(' · '.join(f.get('mots_cles') or [])) or 'Néant'}</p>")

    # 3. Faits non contestés
    contr = f.get("debat_contradictoire")
    h.append("<h2>3. Faits non contestés</h2>" if contr else "<h2>3. Faits allégués, non encore débattus</h2>")
    h.append(_liste([f"{_date(x.get('date'))}{_e(x.get('description'))}{_src(x)}"
                     for x in cut(f.get("faits_non_contestes"))]))

    # 4. Faits contestés
    h.append("<h2>4. Faits contestés</h2>")
    fc = cut(f.get("faits_contestes"))
    if fc:
        rows = ""
        for x in fc:
            def cell(k):
                v = x.get(k)
                return f"{_e(v['texte'])}{_src(v)}" if v else '<span class="muted">—</span>'
            rows += f"<tr><td colspan=\"2\"><b>{_e(x.get('objet'))}</b></td></tr><tr><td>{cell('demandeur')}</td><td>{cell('defendeur')}</td></tr>"
        h.append(f"<table><tr><th>Demandeur</th><th>Défendeur</th></tr>{rows}</table>")
    else:
        h.append('<p class="muted">Néant</p>')

    # 5. Frise de la procédure
    h.append("<h2>5. Frise de la procédure</h2>")
    h.append(_liste([f"{_date(x.get('date'))}{_e(x.get('description'))}{_src(x)}"
                     for x in cut(f.get("frise_procedure"))]))

    # 6. Moyens et prétentions (deux colonnes symétriques)
    h.append("<h2>6. Moyens et prétentions</h2>")

    def col(cote):
        moy = "".join(f"<li><b>{_e(m.get('intitule'))}</b> : {_e(m.get('expose'))}{_src(m)}</li>"
                      for m in cut(f.get(f"moyens_{cote}")))
        pre = "".join(f"<li>{_e(p.get('texte'))}{_src(p)}</li>" for p in cut(f.get(f"pretentions_{cote}")))
        return (f"<p><b>Moyens</b></p><ul>{moy or '<li>Néant</li>'}</ul>"
                f"<p><b>Prétentions</b></p><ul>{pre or '<li>Néant</li>'}</ul>")
    h.append(f"<table><tr><th>Demandeur</th><th>Défendeur</th></tr><tr><td>{col('demandeur')}</td><td>{col('defendeur')}</td></tr></table>")

    # 7. Textes et jurisprudence cités par les parties
    h.append("<h2>7. Textes et jurisprudence cités par les parties</h2>")
    h.append(_liste([f"{'Jurisprudence' if t.get('type') == 'jurisprudence' else 'Texte'} : {_e(t.get('reference'))}"
                     f" — cité par {_e(', '.join(t.get('cite_par') or [])) or 'n.c.'}{_src(t)}"
                     for t in cut(f.get("textes_cites"))]))

    # 8. Pièces
    h.append("<h2>8. Pièces</h2>")
    h.append(_liste([f"n° {_e(p.get('numero'))} — {_e(p.get('intitule'))}"
                     + (f" ({_e(p['cote'])})" if p.get("cote") else "") for p in cut(f.get("pieces"))]))

    # 9. Points de vigilance procédurale
    h.append("<h2>9. Points de vigilance procédurale</h2>")
    vig = []
    for v in cut(f.get("vigilance")):
        t = f"<b>{_e(v.get('objet'))}</b>"
        if v.get("texte_invoque"):
            t += f" — texte invoqué : {_e(v['texte_invoque'])}"
        if v.get("delai"):
            t += f" — délai : {_e(v['delai'])}"
        if v.get("dates_utiles"):
            t += f" — dates utiles : {_e('; '.join(v['dates_utiles']))}"
        vig.append(t + _src(v) + ' <span class="muted">— à vérifier par le magistrat</span>')
    h.append(_liste(vig))

    return f"<html><body>{''.join(h)}</body></html>"


def _rendre(html: str, taille: float) -> tuple[bytes, int]:
    story = pymupdf.Story(html=html, user_css=CSS + f"body {{ font-size: {taille}pt; }}")
    mediabox = pymupdf.paper_rect("a4")
    zone = mediabox + MARGES
    flux = io.BytesIO()
    writer = pymupdf.DocumentWriter(flux)
    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(zone)
        story.draw(dev)
        writer.end_page()
    writer.close()
    doc = pymupdf.open("pdf", flux.getvalue())
    n = len(doc)
    doc.close()
    return flux.getvalue(), n


def synthese_pdf(fiche: dict) -> bytes:
    """Rend la fiche en réduisant progressivement la taille du corps, puis le nombre d'éléments, jusqu'à ≤ 4 pages."""
    resultat = None
    for limite in (None, 12, 8, 5, 3):
        html = _html(fiche, limite)
        for taille in TAILLES:
            resultat = _rendre(html, taille)
            if resultat[1] <= MAX_PAGES:
                return _pied(resultat[0], tronque=limite is not None)
    return _pied(resultat[0], tronque=True)


def _pied(pdf: bytes, tronque: bool) -> bytes:
    doc = pymupdf.open("pdf", pdf)
    total = min(len(doc), MAX_PAGES)
    if len(doc) > MAX_PAGES:
        doc.delete_pages(MAX_PAGES, len(doc) - 1)
    note = " — extraits : version abrégée, voir la fiche complète à l'écran" if tronque else ""
    for i, page in enumerate(doc, start=1):
        r = page.rect
        page.insert_text((MARGES[0], r.height - 28), f"MagistrIA — {BANDEAU}{note}", fontsize=7, color=(0.4, 0.4, 0.4))
        page.insert_text((r.width - 90, r.height - 28), f"Page {i}/{total}", fontsize=7, color=(0.4, 0.4, 0.4))
    out = doc.tobytes()
    doc.close()
    return out
