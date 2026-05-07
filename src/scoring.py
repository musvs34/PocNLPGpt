def calculate_final_score(alerts, config):
    if not alerts:
        return 0
    if any(alert["type_detection"] == "mot interdit exact" for alert in alerts):
        return 100
    score = sum(int(alert.get("score_unitaire", 0)) for alert in alerts)
    if len(alerts) > 1:
        score += int(config["score"].get("occurrence_multiple", 0))
    return min(score, 100)


def determine_status(score):
    if score == 0:
        return "Conforme apparent"
    if score < 30:
        return "Risque faible"
    if score < 60:
        return "À surveiller"
    if score < 80:
        return "À contrôler"
    if score < 100:
        return "Risque fort"
    return "Non conforme probable"
