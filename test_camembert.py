import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))

from camembert_utils import semantic_similarity, find_similar_terms

# Test de similarité
sim = semantic_similarity("malade", "diabète")
print(f"Similarité malade-diabète : {sim:.2f}")

# Test de recherche de termes similaires
candidates = ["diabète", "cancer", "asthme", "voiture", "maison"]
similar = find_similar_terms("malade", candidates, 0.5)
print("Termes similaires à 'malade' :", similar)