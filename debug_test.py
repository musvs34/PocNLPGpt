import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))

from normalize_text import normalize_text
from detection import contains_expression

text = "L'adhérent est diabétique et nécessite une couverture adaptée à ses besoins médicaux spécifiques."
normalized = normalize_text(text)
print('Texte normalisé:', repr(normalized))
print('Contient diabetique:', contains_expression(normalized, 'diabetique'))