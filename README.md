# MagistrIA

**Prise en main des dossiers — sans juger à la place du juge.**
Hackathon Microsoft *AI x Justice* — défi « Accélérer l'analyse et la gestion des dossiers ».

MagistrIA reçoit les actes d'un dossier civil (assignation, conclusions). Pour chaque dossier, il produit une
**fiche de synthèse standardisée, neutre et sourcée**, qui devient le premier écran du magistrat.
La fiche s'affiche dans un tableau de bord **trié selon des critères procéduraux explicables**.

## Ce que fait le MVP

1. On dépose les PDF d'un dossier (assignation, conclusions). On peut ajouter des conclusions plus tard : la fiche est alors régénérée sur l'**ensemble** des actes.
2. Le texte est extrait **page par page** (PyMuPDF), puis envoyé à **Mistral Large sur Azure AI Foundry** (région UE).
3. La fiche contient, dans l'ordre :
   identification · mots-clés · faits non contestés · faits contestés (en vis-à-vis) · frise de la procédure ·
   moyens et prétentions (en vis-à-vis) · textes et jurisprudence cités par les parties (liens Légifrance) · pièces ·
   points de vigilance procédurale.
4. Chaque élément renvoie à sa source (`A · p. 4 · §12`). Un clic ouvre le PDF à la bonne page.
5. Le dossier apparaît dans le tableau de bord, que l'on peut trier (priorité, échéance, date) et filtrer (matière, article, mot-clé, partie).

## Garde-fous

| Exigence du défi | Mise en œuvre |
|---|---|
| Aucune appréciation du fond, aucun « score de mérite » | Le prompt interdit toute appréciation, tout pronostic et tout adjectif évaluatif. Un contrôle automatique détecte le vocabulaire décisionnel (« prescrit », « irrecevable », « bien fondé »…) dans les sections rédigées par l'outil. |
| Chaque synthèse renvoie à ses sources | Chaque élément porte une source (acte, page, §, extrait littéral). **Chaque extrait est revérifié mot pour mot dans le PDF** : ✓ s'il est retrouvé, ⚠ s'il faut le contrôler. |
| Principe du contradictoire | Deux colonnes demandeur / défendeur strictement symétriques (même largeur, même style, ordre fixe), au discours indirect (« X soutient que… »). Les faits ne sont qualifiés de « contestés » ou « non contestés » que si les deux côtés ont conclu. Sinon, ils sont affichés comme « faits allégués, non encore débattus ». |
| Priorisation procédurale et explicable | Ordre : urgence invoquée, puis échéance la plus proche, puis ancienneté. Le motif est affiché pour chaque dossier. |
| Pas d'hallucination juridique | Seuls les textes et décisions **cités par les parties** sont repris, sans aucun ajout par le modèle. |
| Prescription / recevabilité | Présentées comme « points de vigilance procédurale » (dates utiles, texte invoqué, délai), avec « à vérifier par le magistrat ». L'outil ne conclut jamais. |
| Validation humaine systématique | Toute fiche porte le statut « brouillon IA — à valider ». |

## Modèle local (Ollama)

Aucune donnée ne quitte la machine : `ollama pull llama3.2` (ou `qwen2.5:14b`, `mistral-nemo`…), puis dans `backend/.env` :
`LLM_PROVIDER=ollama`, `OLLAMA_MODEL=<modèle>`. `GET /api/status` indique le fournisseur et les modèles installés.
Export standardisé : `GET /api/dossiers/{id}/synthese.pdf` (A4, 4 pages maximum, bouton « Exporter la synthèse »).

## Lancer le projet

Prérequis : Python 3.11+ et Node 18+.

```bash
# Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # renseigner AZURE_AI_ENDPOINT / AZURE_AI_KEY / AZURE_AI_MODEL
.venv/bin/python -m app.seed  # (optionnel) 3 dossiers FICTIFS pour peupler le tableau de bord
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (autre terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Test sans interface :

```bash
cd backend
.venv/bin/python -m app.cli ../samples/assignation.pdf ../samples/conclusions.pdf
```

### Mode démo (secours pour le pitch)

Chaque fiche générée est mise en cache dans `backend/data/cache/`. Si le modèle est injoignable, ou avec
`MAGISTRIA_MODE=demo` dans `.env`, la fiche est reprise du cache pour les mêmes actes.
**Avant le pitch : analysez une fois vos dossiers de démo avec le réseau**, ils resteront ensuite disponibles hors ligne.

## Données et confidentialité

- **Aucun acte n'est versionné** : `samples/`, `backend/data/` et `*.pdf` sont dans `.gitignore` (le repo est public).
- MVP : SQLite local. Les actes ne sont envoyés qu'au déploiement Azure du modèle, en région UE.
- Version cible : hébergement dans l'infrastructure du ministère (ou un cloud qualifié SecNumCloud). Accès réservé au magistrat et à son équipe.

## Architecture

```
backend/app/
  extract.py   PDF -> texte par page
  prompts.py   règles de neutralité / contradictoire / citations
  llm.py       Mistral sur Azure AI Foundry, sortie JSON validée (Pydantic), 1 réparation automatique
  verify.py    vérification des extraits, vocabulaire décisionnel, liens Légifrance
  pipeline.py  orchestration + cache
  priorite.py  critères procéduraux de priorisation
  main.py      API FastAPI
frontend/src/
  pages/Dashboard.jsx   dépôt + tableau triable
  pages/Fiche.jsx       fiche de synthèse en vis-à-vis
```

## À terme

- Intégration au flux **e-barreau / Portalis** : la fiche est générée dès la réception de l'acte.
- Validation et correction de la fiche par le magistrat, avec historique.
- Export PDF de la fiche.
- Vérification des textes via l'API Légifrance et de la jurisprudence via Judilibre (PISTE).
- Vraie similarité entre dossiers et statistiques agrégées pour les chefs de juridiction.
