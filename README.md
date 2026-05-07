# Contrôle RGPD Article 9 - Assurance vie

Projet Python local pour analyser des PDF en français et identifier les documents susceptibles de contenir des termes sensibles Article 9 RGPD.

## Principes

- Aucun appel API externe.
- Traitement local uniquement.
- Paramétrage par fichiers CSV et YAML.
- Détection explicable : mot exact, lemme, famille lexicale, synonyme, mot proche.
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

## Référentiels

```text
input/referentiel/mots_interdits.csv
input/referentiel/synonymes.csv
input/referentiel/familles_lexicales.csv
input/referentiel/whitelist.csv
```

## Notebooks

```text
notebooks/01_parametrage_lancement.ipynb
notebooks/02_analyse_resultats.ipynb
```

## Scoring

- Mot interdit exact : score final 100, non conforme probable.
- Lemme : risque fort paramétrable.
- Famille lexicale : risque fort paramétrable.
- Synonyme métier : risque fort paramétrable.
- Mot proche : alerte de similarité orthographique.

Le score est plafonné à 100.
