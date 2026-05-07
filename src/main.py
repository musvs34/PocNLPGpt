from pathlib import Path

from detection import analyze_document
from export_results import export_results
from extract_pdf import extract_text_from_pdf
from load_referential import load_config, load_referentials

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = PROJECT_ROOT / "input" / "pdf"
REFERENTIEL_DIR = PROJECT_ROOT / "input" / "referentiel"
CONFIG_FILE = PROJECT_ROOT / "config" / "scoring.yaml"
OUTPUT_CSV = PROJECT_ROOT / "output" / "resultats_controle.csv"
OUTPUT_XLSX = PROJECT_ROOT / "output" / "resultats_controle.xlsx"


def main():
    config = load_config(CONFIG_FILE)
    referentials = load_referentials(REFERENTIEL_DIR)
    results = []

    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"Aucun PDF trouvé dans {PDF_DIR}")
        return

    for pdf_path in pdf_files:
        print(f"Analyse : {pdf_path.name}")
        text_by_page = extract_text_from_pdf(pdf_path)
        results.extend(analyze_document(pdf_path, text_by_page, referentials, config))

    output_excel = OUTPUT_XLSX if config.get("sortie", {}).get("format_excel", True) else None
    export_results(results, OUTPUT_CSV, output_excel)
    print(f"Résultats CSV : {OUTPUT_CSV}")
    if output_excel:
        print(f"Résultats Excel : {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
