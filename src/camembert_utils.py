from functools import lru_cache
import torch
from transformers import CamembertTokenizer, CamembertModel

MODEL_NAME = "camembert-base"


@lru_cache(maxsize=1)
def load_camembert():
    """Charge le modèle CamemBERT localement."""
    try:
        tokenizer = CamembertTokenizer.from_pretrained(MODEL_NAME)
        model = CamembertModel.from_pretrained(MODEL_NAME)
        model.eval()  # Mode évaluation
        return tokenizer, model
    except Exception as e:
        raise RuntimeError(f"Erreur chargement CamemBERT : {e}. Téléchargez avec internet.")


def get_embedding(text: str) -> torch.Tensor:
    """Calcule l'embedding d'un texte avec CamemBERT."""
    tokenizer, model = load_camembert()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    # Moyenne des embeddings des tokens
    return outputs.last_hidden_state.mean(dim=1).squeeze()


def semantic_similarity(word1: str, word2: str) -> float:
    """Calcule la similarité cosinus entre deux mots."""
    emb1 = get_embedding(word1)
    emb2 = get_embedding(word2)
    cos_sim = torch.nn.functional.cosine_similarity(emb1, emb2, dim=0)
    return cos_sim.item()


def find_similar_terms(seed: str, candidates: list, threshold: float = 0.7) -> list:
    """Trouve les termes similaires à un seed parmi une liste de candidats."""
    similar = []
    for candidate in candidates:
        if candidate == seed:
            continue
        sim = semantic_similarity(seed, candidate)
        if sim >= threshold:
            similar.append((candidate, sim))
    return sorted(similar, key=lambda x: x[1], reverse=True)


def expand_domain_with_camembert(domain_seeds: dict, all_candidates: list, threshold: float = 0.7) -> dict:
    """Enrichit les domaines avec des termes similaires via CamemBERT."""
    expanded = {}
    for domain, seeds in domain_seeds.items():
        expanded[domain] = set(seeds)  # Copie des seeds originaux
        for seed in seeds:
            similar = find_similar_terms(seed, all_candidates, threshold)
            for term, _ in similar:
                expanded[domain].add(term)
    return expanded