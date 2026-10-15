# MagistrIA — point d'étape pour l'équipe

## Le projet
Hackathon Microsoft « AI x Justice », thème : « Désengorger sans juger à la place du juge ».
MagistrIA reçoit les actes d'un dossier (assignation, conclusions) et produit une **fiche de synthèse neutre et sourcée**.
Les fiches arrivent dans un **tableau de bord** qui se trie par priorité procédurale, matière, date, article et mot-clé.

Garde-fous du jury qu'on respecte :
- aucune appréciation du fond, aucun « score de mérite » ;
- priorisation uniquement sur des critères procéduraux, expliqués à l'écran ;
- chaque élément de la fiche renvoie à sa source (acte, page, §, extrait) ;
- validation humaine : chaque fiche porte le statut « brouillon IA ».

## Décisions prises
- **Modèle** : Mistral Large via **Azure AI Foundry**, région UE, payé avec nos crédits Azure (on joue souveraineté + écosystème Microsoft).
- **Stack** : FastAPI (Python) + React (Vite, JS sans TypeScript) + SQLite.
- **Le repo GitHub est PUBLIC** : aucun document réel ne doit être commité. `samples/`, `backend/data/`, `*.pdf` et `.env` sont dans `.gitignore`.
- **Synthèse au niveau du dossier**, pas document par document. On peut ajouter des conclusions à un dossier existant : la fiche est régénérée sur tous les actes.
  - Les conclusions des avocats sont des actes à part entière.
  - Si une partie a plusieurs jeux de conclusions, ce sont les dernières (récapitulatives) qui comptent.
  - S'il n'y a qu'un acte, les faits sont affichés comme « faits allégués, non encore débattus ».
- **On extrait le texte nous-mêmes avec PyMuPDF**, page par page, au lieu de laisser le LLM lire le PDF. C'est ce qui permet les liens « p. 4 § 12 » et la vérification que chaque citation existe vraiment dans le document.
- **Points de vigilance procédurale** à la place de « recevabilité / prescription » : dates utiles, texte invoqué, délai, avec la mention « à vérifier par le magistrat ». L'outil n'écrit jamais « prescrit » ni « irrecevable ».
- **Jurisprudence et articles** : uniquement ceux cités par les parties, avec un lien Légifrance. Rien n'est ajouté par l'IA.
- **Contradictoire** : demandeur et défendeur en deux colonnes symétriques, au discours indirect (« X soutient que… »).
- **Pitch** : dire « s'intègre au flux e-barreau / Portalis » plutôt que « extension RPVA » (le RPVA est le réseau des avocats). À confirmer par l'équipe.
- **Reporté en « à terme »** : export PDF, validation éditable, vraie similarité entre dossiers, API Légifrance/Judilibre.

## Contenu de la fiche (dans cet ordre)
1. Identification : parties, avocats, RG, juridiction et chambre, nature de l'affaire, date d'introduction
2. Mots-clés
3. Frise des faits non contestés
4. Faits contestés : demandeur | défendeur
5. Frise de la procédure
6. Moyens et prétentions, en deux colonnes
7. Textes et jurisprudence cités par les parties (liens Légifrance)
8. Liste des pièces
9. Points de vigilance procédurale

En plus : bandeau « Synthèse IA — brouillon à valider — pas une analyse du fond », alertes (sources non retrouvées, vocabulaire décisionnel) et encart « dossiers de même matière / mots-clés communs ».

## Arborescence
```
magistrIA/
  .gitignore
  backend/
    requirements.txt  .env.example
    app/
      main.py      API FastAPI (/api/...)
      schema.py    schéma Pydantic de la fiche
      prompts.py   prompt système (neutralité, sources, contradictoire)
      extract.py   PyMuPDF, texte page par page + balises <<<ACTE A | PAGE n>>>
      llm.py       appel Azure AI Foundry (compatible OpenAI), sortie JSON, 1 essai de réparation
      verify.py    vérifie les extraits cités, repère le vocabulaire décisionnel, construit les URL Légifrance
      pipeline.py  actes → LLM → vérifications → base (+ cache de secours)
      priorite.py  tri : urgence invoquée → échéance la plus proche → ancienneté
      db.py        SQLite dans backend/data/
      seed.py      3 dossiers FICTIFS pour remplir le tableau de bord
      cli.py       test en ligne de commande, sans interface
  frontend/        React + Vite (en cours de développement)
  samples/         nos PDF anonymisés (gitignorés, à copier en local)
```

## Lancer le projet
Backend :
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # remplir AZURE_AI_ENDPOINT, AZURE_AI_KEY, AZURE_AI_MODEL
.venv/bin/python -m app.seed            # dossiers fictifs (option --reset)
.venv/bin/uvicorn app.main:app --port 8000
```
Test du pipeline sans l'interface :
```bash
.venv/bin/python -m app.cli ../samples/assignation.pdf ../samples/conclusions.pdf
```
Frontend (une fois terminé) :
```bash
cd frontend && npm install && npm run dev   # http://localhost:5173, /api renvoyé vers :8000
```

## Routes de l'API
- `GET  /api/status` : LLM configuré ou non, mode
- `POST /api/dossiers` : upload de 1 à n PDF (champ `files`), analyse en tâche de fond
- `POST /api/dossiers/{id}/actes` : ajouter des conclusions, puis régénérer la fiche
- `POST /api/dossiers/{id}/relancer` : relancer l'analyse
- `GET  /api/dossiers` : liste triée par priorité, avec les motifs
- `GET  /api/dossiers/{id}` : fiche, documents et dossiers similaires
- `GET  /api/files/{doc_id}` : le PDF (pour ouvrir à une page : `#page=N`)
- `DELETE /api/dossiers/{id}`

## Mode démo et secours pendant le pitch
- Chaque fiche générée est mise en cache dans `backend/data/cache/`.
- Si Azure est injoignable, ou si `.env` contient `MAGISTRIA_MODE=demo`, la fiche en cache est réutilisée pour les mêmes actes.
- **Avant le pitch** : générer une fois les fiches des dossiers de démo avec le réseau, pour remplir le cache.

## Ce qui est testé
- Extraction et vérification des sources : une citation inventée est signalée ⚠, une page erronée est corrigée, « prescrite » déclenche une alerte.
- API : le seed, la liste triée par priorité et l'upload fonctionnent. Sans clé Azure, l'analyse passe en erreur avec un message clair.
- **Pas encore testé** : un vrai appel à Mistral sur Azure (il manque la clé) et le frontend.

## Reste à faire
- [ ] Récupérer endpoint, clé et nom du déploiement Mistral dans Azure AI Foundry → `backend/.env`
- [ ] Copier l'assignation et les conclusions anonymisées (fraude bancaire) dans `samples/` (jamais commitées), puis lancer `app.cli`
- [ ] Relire la fiche obtenue : neutralité, symétrie, sources
- [ ] Frontend : tableau de bord (upload, tri, filtres) + fiche (vis-à-vis, liens vers les sources)
- [ ] README et argumentaire du pitch (problème, utilisateurs, démo, limites et éthique)
- [ ] Vérifier l'anonymisation des PDF, y compris leurs métadonnées
