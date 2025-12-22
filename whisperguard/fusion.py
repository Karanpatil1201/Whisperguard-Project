"""Combine rule-based and ML scores to produce a risk level."""

def fuse_scores(rule_score, ml_scores, sensitivity=0.5, whitelist=False):
    """Return risk level and combined score.

    rule_score: float (0..1) energy ratio or binary
    ml_scores: dict of class->confidence
    sensitivity: user setting (0..1) increases alerts
    whitelist: if True, force safe
    """
    if whitelist:
        return "SAFE", 0.0
    # Consider maximum non-normal class confidence
    non_normal = max([v for k, v in ml_scores.items() if k != "Normal"] + [0.0])
    combined = max(rule_score, non_normal)
    # sensitivity shifts thresholds
    if combined >= 0.85 * (1.0 - sensitivity * 0.5):
        return "THREAT", combined
    if combined >= 0.6 * (1.0 - sensitivity * 0.5):
        return "SUSPICIOUS", combined
    return "SAFE", combined
