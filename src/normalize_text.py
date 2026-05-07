import re
import unicodedata


def remove_accents(text: str) -> str:
    return ''.join(
        char for char in unicodedata.normalize('NFD', str(text))
        if unicodedata.category(char) != 'Mn'
    )


def normalize_text(text: str) -> str:
    text = str(text).lower()
    text = remove_accents(text)
    text = re.sub(r"[^a-z0-9œæ\-\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
