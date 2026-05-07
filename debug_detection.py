import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path('src').resolve()))

from normalize_text import normalize_text
from detection import contains_expression

# Simuler le texte du PDF
text = "L'adhérent est diabétique et nécessite une couverture adaptée à ses besoins médicaux spécifiques."
normalized_text = normalize_text(text)
print("Texte normalisé:", repr(normalized_text))

# Simuler le seed
seed = "diabetique"
print("Seed:", repr(seed))
print("Contient seed:", contains_expression(normalized_text, seed))

# Simuler les domaines
domaines = pd.DataFrame({
    "domaine": ["sante"],
    "variante": ["diabetique"],
    "categorie": ["sante"],
    "gravite": [85],
    "commentaire": ["test"]
})

config = {
    "detection": {
        "domaines_a_analyser": ["sante"],
        "seuil_similarite_semantique": 0.6
    }
}

from detection import detect_domain_semantics

tokens = []  # Pas de tokens pour test
alerts = detect_domain_semantics("test.pdf", 1, normalized_text, tokens, domaines, config)
print("Alertes détectées:", alerts)