from pathlib import Path
from typing import List, Dict

import pandas as pd

COLUMNS = [
    "document", "score", "score_unitaire", "statut", "terme_detecte", "terme_reference",
    "type_detection", "categorie", "motif", "page", "contexte"
]


def export_results(results: List[Dict], output_csv: Path, output_excel: Path | None = None):
    df = pd.DataFrame(results)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    if output_excel:
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="alertes")
            synthese = df.groupby("document", as_index=False).agg(
                score=("score", "max"), statut=("statut", "first"), nb_alertes=("terme_detecte", lambda s: (s != "").sum())
            ).sort_values("score", ascending=False)
            synthese.to_excel(writer, index=False, sheet_name="synthese")
