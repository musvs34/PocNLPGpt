from typing import Tuple

from rapidfuzz import fuzz

from lemmatizer import get_lemmas, get_token_texts, lemmatize_text, load_nlp
from normalize_text import normalize_text
from scoring import calculate_final_score, determine_status


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

        needs_tokens = any([
            config["detection"].get("activer_lemmatisation", True),
            config["detection"].get("activer_synonymes_automatiques", True),
        ])
        page_tokens = lemmatize_text(text) if needs_tokens else []

        alerts.extend(detect_exact_terms(pdf_path.name, page_number, text, referentials["mots_interdits"], config))

        if config["detection"].get("activer_lemmatisation", True):
            alerts.extend(detect_by_lemma(pdf_path.name, page_number, text, page_tokens, referentials["mots_interdits"], config))

        if config["detection"].get("activer_synonymes_automatiques", True):
            alerts.extend(detect_automatic_synonyms(pdf_path.name, page_number, text, page_tokens, referentials["mots_interdits"], config))

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
            "score_unitaire": "",
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
                "lemme", row["categorie"], f"Forme lemmatisee proche du terme interdit : {row['terme']}", text, config
            ))
    return alerts


def detect_automatic_synonyms(document, page, text, tokens, mots_interdits, config):
    alerts = []
    if not tokens:
        return alerts

    nlp = load_nlp()
    threshold = float(config["detection"].get("seuil_synonyme_automatique", 0.72))
    min_len = int(config["detection"].get("ignorer_mots_trop_courts", 4))
    allowed_pos = set(config["detection"].get("pos_synonymes_automatiques", ["NOUN", "PROPN", "ADJ"]))
    matched_terms = set()

    forbidden_vectors = []
    for _, row in mots_interdits.iterrows():
        terme = normalize_text(row["terme"])
        if not terme:
            continue
        terme_doc = nlp(terme)
        if not terme_doc.has_vector or not terme_doc.vector_norm:
            continue
        forbidden_vectors.append((row, terme, terme_doc.vector, terme_doc.vector_norm))

    if not forbidden_vectors:
        return alerts

    for token in tokens:
        candidate = normalize_text(str(token["lemma"] or token["text"]))
        detected_text = normalize_text(str(token["text"]))
        if len(candidate) < min_len or not candidate.isalpha():
            continue
        if allowed_pos and token.get("pos") not in allowed_pos:
            continue

        candidate_lex = nlp.vocab[candidate]
        if not candidate_lex.has_vector or not candidate_lex.vector_norm:
            continue

        for row, terme, forbidden_vector, forbidden_norm in forbidden_vectors:
            if candidate == terme or detected_text == terme:
                continue
            match_key = (detected_text, row["terme"], row["categorie"])
            if match_key in matched_terms:
                continue

            similarity = candidate_lex.vector.dot(forbidden_vector) / (candidate_lex.vector_norm * forbidden_norm)
            if similarity >= threshold:
                matched_terms.add(match_key)
                alerts.append(make_alert(
                    document, page, config["score"]["synonyme_automatique"],
                    detected_text, row["terme"], "synonyme automatique", row["categorie"],
                    f"Terme proche semantiquement de : {row['terme']} ({similarity:.2f})",
                    text, config
                ))
                break

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
