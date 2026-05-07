from typing import Dict, List, Tuple

from rapidfuzz import fuzz

from lemmatizer import get_lemmas, get_token_texts, lemmatize_text, load_nlp
from normalize_text import normalize_text
from scoring import calculate_final_score, determine_status
from camembert_utils import expand_domain_with_camembert, semantic_similarity


def analyze_document(pdf_path, text_by_page, referentials, config):
    alerts = []

    for page_data in text_by_page:
        page_number = page_data["page"]
        raw_text = page_data["text"] or ""
        text = normalize_text(raw_text)

        if not text:
            continue

        text = apply_whitelist(text, referentials["whitelist"])
        if not text.strip():
            continue

        page_tokens = lemmatize_text(text) if config["detection"].get("activer_lemmatisation", True) else []

        alerts.extend(detect_exact_terms(pdf_path.name, page_number, text, referentials["mots_interdits"], config))

        if config["detection"].get("activer_lemmatisation", True):
            alerts.extend(detect_by_lemma(pdf_path.name, page_number, text, page_tokens, referentials["mots_interdits"], config))

        if config["detection"].get("activer_familles_lexicales", True):
            alerts.extend(detect_lexical_families(pdf_path.name, page_number, text, page_tokens, referentials["familles_lexicales"], config))

        if config["detection"].get("activer_synonymes", True):
            alerts.extend(detect_synonyms(pdf_path.name, page_number, text, referentials["synonymes"], config))

        if config["detection"].get("activer_domaines_semantiques", True):
            alerts.extend(detect_domain_semantics(pdf_path.name, page_number, text, page_tokens, referentials["domaines_semantiques"], config))

        if config["detection"].get("activer_mots_proches", True):
            alerts.extend(detect_close_words(pdf_path.name, page_number, text, referentials["mots_interdits"], config))

    if config["detection"].get("dedoublonner_alertes", True):
        alerts = deduplicate_alerts(alerts)

    final_score = calculate_final_score(alerts, config)
    statut = determine_status(final_score)

    if not alerts:
        return [{
            "document": pdf_path.name,
            "score": 0,
            "statut": statut,
            "terme_detecte": "",
            "terme_reference": "",
            "type_detection": "",
            "categorie": "",
            "motif": "",
            "page": "",
            "contexte": "",
        }]

    for alert in alerts:
        alert["score"] = final_score
        alert["statut"] = statut
    return alerts


def make_alert(document, page, score, detected, reference, detection_type, category, motif, text, config):
    return {
        "document": document,
        "score": "",
        "score_unitaire": int(score),
        "statut": "",
        "terme_detecte": detected,
        "terme_reference": reference,
        "type_detection": detection_type,
        "categorie": category,
        "motif": motif,
        "page": page,
        "contexte": extract_context(text, normalize_text(str(detected)), config),
    }


def detect_exact_terms(document, page, text, mots_interdits, config):
    alerts = []
    for _, row in mots_interdits.iterrows():
        terme = normalize_text(row["terme"])
        if contains_expression(text, terme):
            alerts.append(make_alert(
                document, page, config["score"]["mot_interdit_exact"], row["terme"], row["terme"],
                "mot interdit exact", row["categorie"], row["commentaire"], text, config
            ))
    return alerts


def detect_by_lemma(document, page, text, tokens, mots_interdits, config):
    alerts = []
    lemmas = get_lemmas(tokens)
    token_texts = get_token_texts(tokens)

    for _, row in mots_interdits.iterrows():
        terme = normalize_text(row["terme"])
        terme_lemmas = get_lemmas(lemmatize_text(terme))
        if not terme_lemmas:
            continue

        found_text = None
        if len(terme_lemmas) == 1:
            target = terme_lemmas[0]
            for idx, lemma in enumerate(lemmas):
                if lemma == target and token_texts[idx] != terme:
                    found_text = token_texts[idx]
                    break
        else:
            for i in range(len(lemmas) - len(terme_lemmas) + 1):
                if lemmas[i:i + len(terme_lemmas)] == terme_lemmas:
                    found_text = " ".join(token_texts[i:i + len(terme_lemmas)])
                    break

        if found_text:
            alerts.append(make_alert(
                document, page, config["score"]["lemme"], found_text, row["terme"],
                "lemme", row["categorie"], f"Forme lemmatisée proche du terme interdit : {row['terme']}", text, config
            ))
    return alerts


def detect_lexical_families(document, page, text, tokens, familles_lexicales, config):
    alerts = []
    lemmas = set(get_lemmas(tokens)) if tokens else set()
    token_texts = set(get_token_texts(tokens)) if tokens else set()

    for _, row in familles_lexicales.iterrows():
        variante = normalize_text(row["variante"])
        detected = False

        if contains_expression(text, variante):
            detected = True
        elif tokens:
            variante_lemmas = set(get_lemmas(lemmatize_text(variante)))
            if variante_lemmas & lemmas or variante_lemmas & token_texts:
                detected = True

        if detected:
            alerts.append(make_alert(
                document, page, int(row.get("gravite") or config["score"]["famille_lexicale"]),
                row["variante"], row["terme_reference"], "famille lexicale", row["categorie"],
                f"Variante métier du terme interdit : {row['terme_reference']}", text, config
            ))
    return alerts


def detect_synonyms(document, page, text, synonymes, config):
    alerts = []
    for _, row in synonymes.iterrows():
        synonyme = normalize_text(row["synonyme"])
        if contains_expression(text, synonyme):
            alerts.append(make_alert(
                document, page, int(row.get("gravite") or config["score"]["synonyme"]),
                row["synonyme"], row["terme_reference"], "synonyme", row["categorie"],
                f"Synonyme métier du terme interdit : {row['terme_reference']}", text, config
            ))
    return alerts


def detect_domain_semantics(document, page, text, tokens, domaines, config):
    alerts = []
    if not tokens:
        tokens = []  # Ensure tokens is a list

    nlp = load_nlp()
    domains_to_analyze = {
        normalize_text(domain)
        for domain in config["detection"].get("domaines_a_analyser", [])
        if domain
    }
    print(f"DEBUG: domains_to_analyze = {domains_to_analyze}")

    domain_entries = [
        row
        for _, row in domaines.iterrows()
        if not domains_to_analyze or normalize_text(row.get("domaine", "")) in domains_to_analyze
    ]
    print(f"DEBUG: domain_entries count = {len(domain_entries)}")
    if not domain_entries:
        return alerts

    domain_seeds = {}
    domain_meta = {}
    for row in domain_entries:
        domaine = normalize_text(row.get("domaine") or row.get("terme_reference") or "")
        variante = normalize_text(row.get("variante", ""))
        if not variante:
            continue
        domain_seeds.setdefault(domaine, set()).add(variante)
        if domaine not in domain_meta:
            domain_meta[domaine] = row

    print(f"DEBUG: domain_seeds = {domain_seeds}")

    # Enrichissement automatique avec CamemBERT si activé
    if config["detection"].get("enrichir_avec_camembert", False):
        all_candidates = [normalize_text(token["text"]) for token in tokens if len(token["text"]) > 3]
        domain_seeds = expand_domain_with_camembert(domain_seeds, all_candidates, config["detection"].get("seuil_similarite_semantique", 0.7))

    similarity_threshold = float(config["detection"].get("seuil_similarite_semantique", 0.60))
    matched_terms = set()
    for domaine, seeds in domain_seeds.items():
        meta = domain_meta.get(domaine, {})
        gravite = int(meta.get("gravite") or config["score"].get("domaines_semantiques", config["score"]["famille_lexicale"]))
        categorie = meta.get("categorie", domaine)
        terme_reference = meta.get("terme_reference") or domaine
        commentaire = meta.get("commentaire", f"Domaine sémantique {domaine}")

        for seed in seeds:
            if contains_expression(text, seed) and seed not in matched_terms:
                print(f"DEBUG: Detected seed '{seed}' in text for domain '{domaine}'")
                matched_terms.add(seed)
                alerts.append(make_alert(
                    document, page, gravite, seed, terme_reference,
                    "domaine sémantique", categorie,
                    commentaire, text, config
                ))

        seed_vectors = []
        for seed in seeds:
            seed_lex = nlp.vocab[seed]
            if seed_lex.has_vector:
                seed_vectors.append((seed, seed_lex))

        for token in tokens:
            lemma = token["lemma"]
            if lemma in seeds or token["text"] in seeds:
                continue
            if len(lemma) < 3 or not lemma.isalpha():
                continue
            token_lex = nlp.vocab[lemma]
            if not token_lex.has_vector:
                continue

            for seed, seed_lex in seed_vectors:
                similarity = token_lex.similarity(seed_lex)
                if similarity >= similarity_threshold:
                    detected_text = token["text"]
                    if detected_text not in matched_terms:
                        matched_terms.add(detected_text)
                        alerts.append(make_alert(
                            document, page, gravite, detected_text, terme_reference,
                            "domaine sémantique", categorie,
                            f"Terme proche sémantiquement du domaine {domaine} (seed={seed}, sim={similarity:.2f})",
                            text, config
                        ))
                    break
    print(f"DEBUG: Total alerts for domains = {len(alerts)}")
    return alerts


def detect_close_words(document, page, text, mots_interdits, config):
    alerts = []
    words = text.split()
    threshold = int(config["detection"]["seuil_similarite_orthographique"])
    min_len = int(config["detection"].get("ignorer_mots_trop_courts", 4))

    for _, row in mots_interdits.iterrows():
        terme = normalize_text(row["terme"])
        if " " in terme or len(terme) < min_len:
            continue
        for word in words:
            if len(word) < min_len or word == terme:
                continue
            similarity = fuzz.ratio(word, terme)
            if similarity >= threshold:
                alerts.append(make_alert(
                    document, page, config["score"]["mot_proche"], word, row["terme"],
                    "mot proche", row["categorie"], f"Mot proche orthographiquement de : {row['terme']} ({similarity:.0f}%)",
                    text, config
                ))
    return alerts


def contains_expression(text: str, expression: str) -> bool:
    if not expression:
        return False
    padded_text = f" {text} "
    padded_expression = f" {expression} "
    return padded_expression in padded_text


def apply_whitelist(text, whitelist):
    cleaned = f" {text} "
    for _, row in whitelist.iterrows():
        expression = normalize_text(row["expression"])
        if expression:
            cleaned = cleaned.replace(f" {expression} ", " ")
    return cleaned.strip()


def extract_context(text, term, config):
    if not config.get("sortie", {}).get("inclure_contexte", True):
        return ""
    words = text.split()
    term_words = term.split()
    context_size = int(config["detection"].get("taille_contexte_mots", 10))
    for i in range(len(words)):
        if words[i:i + len(term_words)] == term_words:
            start = max(0, i - context_size)
            end = min(len(words), i + len(term_words) + context_size)
            return " ".join(words[start:end])
    return ""


def deduplicate_alerts(alerts):
    seen: set[Tuple] = set()
    deduped = []
    for alert in alerts:
        key = (
            alert["document"], alert["page"], normalize_text(alert["terme_detecte"]),
            alert["terme_reference"], alert["type_detection"], alert["categorie"]
        )
        if key not in seen:
            seen.add(key)
            deduped.append(alert)
    return deduped
