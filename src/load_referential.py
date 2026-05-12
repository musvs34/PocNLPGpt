from pathlib import Path
from typing import Dict

import pandas as pd
import yaml


def load_config(config_file: Path) -> Dict:
    with open(config_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _read_csv(path: Path, required_columns: set) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Referentiel manquant : {path}")
    df = pd.read_csv(path, encoding="utf-8")
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans {path.name} : {missing}")
    return df.fillna("")


def load_referentials(referential_dir: Path) -> Dict[str, pd.DataFrame]:
    referential_dir = Path(referential_dir)
    return {
        "mots_interdits": _read_csv(
            referential_dir / "mots_interdits.csv",
            {"terme", "categorie", "gravite", "commentaire"},
        ),
        "whitelist": _read_csv(
            referential_dir / "whitelist.csv",
            {"expression", "categorie"},
        ),
    }
