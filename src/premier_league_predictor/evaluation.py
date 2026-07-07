from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    log_loss,
)
from sklearn.preprocessing import label_binarize

from premier_league_predictor.data import load_matches
from premier_league_predictor.features import build_features

_FEATURE_FLAG_KEYS = (
    "include_rest_days",
    "include_xg_proxy",
    "include_elo",
    "include_multi_window",
    "include_discipline",
    "include_odds_movement",
    "include_multi_bookmaker",
    "include_fixture_congestion",
    "include_halftime",
    "include_opponent_adj",
)


def _feature_kwargs(feature_cfg: dict) -> dict[str, bool]:
    return {k: bool(feature_cfg.get(k, True)) for k in _FEATURE_FLAG_KEYS}


def _drop_metadata_columns(x):
    to_drop = [c for c in ("_season",) if c in x.columns]
    return x.drop(columns=to_drop) if to_drop else x


def _multiclass_brier(y_true, proba, labels) -> float:
    """Mean one-vs-rest Brier score across classes."""
    y_bin = label_binarize(y_true, classes=labels)
    scores = []
    for i in range(len(labels)):
        scores.append(brier_score_loss(y_bin[:, i], proba[:, i]))
    return float(np.mean(scores))


def evaluate_from_config(config: dict) -> dict[str, float]:
    data_cfg = config["data"]
    feature_cfg = config.get("features", {})
    output_cfg = config["output"]

    model_path = Path(output_cfg["model_path"])
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = joblib.load(model_path)

    df = load_matches(csv_path=data_cfg.get("csv_path"), csv_glob=data_cfg.get("csv_glob"))
    x, y = build_features(df, **_feature_kwargs(feature_cfg))
    x = _drop_metadata_columns(x)

    predictions = model.predict(x)
    accuracy = accuracy_score(y, predictions)
    print(classification_report(y, predictions))

    result: dict[str, float] = {"accuracy": float(accuracy)}

    # Log-loss and Brier score (if model supports predict_proba)
    labels = sorted(y.unique())
    try:
        proba = model.predict_proba(x)
        result["log_loss"] = float(log_loss(y, proba, labels=labels))
        result["brier_score"] = _multiclass_brier(np.asarray(y), proba, labels)
    except Exception:
        pass  # model doesn't support predict_proba

    return result
