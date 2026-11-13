"""Detector evaluation against the scenario ground truth (§8.8).

The detector is scored like a classifier: false alarms where nothing was injected, detection
delay after the onset, which layers fired, feature attribution and diagnosis accuracy.
"""

from typing import Any

LAYERS = {"L2": ("feature_psi",), "L3": ("score_psi", "approval_delta_pp"),
          "L4": ("bad_rate_ratio", "auc_drop")}  # fmt: skip


def layers_fired(result: dict[str, Any]) -> set[str]:
    """Layers with at least one signal at SEV-1+ in a batch."""
    s = result["severity"]["signals"]
    return {layer for layer, sigs in LAYERS.items() if any(s[x] >= 1 for x in sigs)}


def _first(results: list[dict[str, Any]], pred) -> int | None:
    return next((r["index"] for r in results if pred(r)), None)


def _delay(first: int | None, onset: int | None) -> int | None:
    return None if first is None or onset is None else first - onset


def alarm_rates(results: list[dict[str, Any]]) -> dict[str, float | int]:
    """Share of batches at SEV-1+ and SEV-2+."""
    n = len(results)
    levels = [r["severity"]["level"] for r in results]
    return {"batches": n, "sev1_plus": sum(v >= 1 for v in levels) / n if n else 0.0,
            "sev2_plus": sum(v >= 2 for v in levels) / n if n else 0.0}  # fmt: skip


def attribution(post: list[dict[str, Any]], truth: list[str]) -> dict[str, Any]:
    """Recall and precision of the features flagged after the onset."""
    flagged = sorted({f for r in post for f in r["severity"]["flagged_features"]})
    hit = set(flagged) & set(truth)
    known = bool(truth)  # no injected feature (S0, S2, S3, S5): attribution is undefined
    return {"flagged": flagged, "truth": truth,
            "recall": len(hit) / len(truth) if known else None,
            "precision": len(hit) / len(flagged) if known and flagged else None}  # fmt: skip


def diagnosis_accuracy(post: list[dict[str, Any]], expected: str) -> dict[str, Any]:
    """Share of alerting post-onset batches whose diagnosis matches the ground truth."""
    alerting = [r for r in post if r["severity"]["level"] >= 1]
    counts: dict[str, int] = {}
    for r in alerting:
        counts[r["diagnosis"]] = counts.get(r["diagnosis"], 0) + 1
    correct = counts.get(expected, 0)
    defined = alerting and expected != "unknown"
    return {"expected": expected, "counts": counts,
            "accuracy": correct / len(alerting) if defined else None}  # fmt: skip


def evaluate(results: list[dict[str, Any]], ground_truth: dict[str, Any]) -> dict[str, Any]:
    """All §8.8 metrics for one scenario."""
    onset = ground_truth["onset_batch"]
    pre = [r for r in results if onset is not None and r["index"] < onset]
    post = [r for r in results if onset is None or r["index"] >= onset]
    control = results if ground_truth["drift_type"] == "none" else pre
    fired = sorted(set().union(*(layers_fired(r) for r in post))) if post else []
    first1 = _first(post, lambda r: r["severity"]["level"] >= 1)
    first2 = _first(post, lambda r: r["severity"]["level"] >= 2)
    expected = ground_truth["expected_layers"]
    return {
        "onset": onset, "false_alarm": alarm_rates(control), "post_onset": alarm_rates(post),
        "first_sev1": first1, "delay_sev1": _delay(first1, onset),
        "first_sev2": first2, "delay_sev2": _delay(first2, onset),
        "layers_expected": expected, "layers_fired": fired,
        "layers_missed": sorted(set(expected) - set(fired)),
        "layers_unexpected": sorted(set(fired) - set(expected)),
        "first_by_layer": {lay: _first(post, lambda r, lay=lay: lay in layers_fired(r))
                           for lay in LAYERS},
        "attribution": attribution(post, ground_truth["drifted_features"]),
        "diagnosis": diagnosis_accuracy(post, ground_truth["expected_diagnosis"]),
    }  # fmt: skip
