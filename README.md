# Controle RGPD Article 9 - Assurance vie

Projet Python local pour analyser des PDF en francais et identifier les documents susceptibles de contenir des termes sensibles Article 9 RGPD.

## Principes

- Aucun appel API externe.
- Traitement local uniquement.
- Parametrage par `mots_interdits.csv`, `whitelist.csv` et `config/scoring.yaml`.
- Detection explicable : mot exact, lemme, synonyme automatique, mot proche.
- Sortie CSV et Excel locales.

## Installation

```bash
pip install -r requirements.txt
python -m spacy download fr_core_news_md
```

## Lancement batch

Placez les PDF dans :

```text
input/pdf/
```

Puis lancez :

```bash
python src/main.py
```

## Referentiels

```text
input/referentiel/mots_interdits.csv
input/referentiel/whitelist.csv
```

`mots_interdits.csv` est la source principale. Chaque ligne fournit le `terme` de reference, sa `categorie`, sa `gravite` et le `commentaire` utilise dans les alertes.

La detection `synonyme automatique` compare les termes presents dans les documents avec les termes de `mots_interdits.csv` par similarite semantique spaCy. L'alerte reprend la categorie du terme de reference.

`whitelist.csv` liste les expressions a ignorer avant analyse pour limiter les faux positifs.

## Notebooks

```text
notebooks/01_parametrage_lancement.ipynb
notebooks/02_analyse_resultats.ipynb
```

## Scoring

- Mot interdit exact : score final 100, non conforme probable.
- Lemme : risque fort parametrable.
- Synonyme automatique : risque fort parametrable.
- Mot proche : alerte de similarite orthographique.

Le score est plafonne a 100.
