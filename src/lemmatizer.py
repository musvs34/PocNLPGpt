from functools import lru_cache
from typing import Dict, List

import spacy

from normalize_text import normalize_text

MODEL_NAME = "fr_core_news_md"


@lru_cache(maxsize=1)
def load_nlp():
    """Charge le modèle spaCy local une seule fois."""
    try:
        return spacy.load(MODEL_NAME, disable=["ner"])
    except OSError as exc:
        raise RuntimeError(
            f"Le modèle spaCy {MODEL_NAME} n'est pas installé. "
            f"Exécuter : python -m spacy download {MODEL_NAME}"
        ) from exc


def lemmatize_text(text: str) -> List[Dict[str, object]]:
    nlp = load_nlp()
    normalized = normalize_text(text)
    doc = nlp(normalized)

    tokens = []
    for token in doc:
        if token.is_space or token.is_punct:
            continue
        if not token.text.strip():
            continue
        tokens.append({
            "text": token.text.lower(),
            "lemma": normalize_text(token.lemma_),
            "pos": token.pos_,
            "start": token.idx,
            "end": token.idx + len(token.text),
        })
    return tokens


def get_lemmas(tokens: List[Dict[str, object]]) -> List[str]:
    return [str(token["lemma"]) for token in tokens]


def get_token_texts(tokens: List[Dict[str, object]]) -> List[str]:
    return [str(token["text"]) for token in tokens]
