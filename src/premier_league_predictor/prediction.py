from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

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


def _drop_metadata_columns(x: pd.DataFrame) -> pd.DataFrame:
    to_drop = [c for c in ("_season",) if c in x.columns]
    return x.drop(columns=to_drop) if to_drop else x


def _build_fixture_df(
    fixtures: list[dict],
) -> pd.DataFrame:
    """Build a DataFrame from a list of fixture dicts.

    Each dict must have at minimum ``Date``, ``HomeTeam``, ``AwayTeam``.
    Odds columns and other stats are optional.
    """
    return pd.DataFrame(fixtures)


def predict_fixtures(
    config: dict,
    fixtures: list[dict] | pd.DataFrame,
) -> list[dict]:
    """Predict outcomes for upcoming fixtures.

    Parameters
    ----------
    config : dict
        Full YAML config (same as used for training).
    fixtures : list[dict] | pd.DataFrame
        Upcoming matches.  Each row needs at least ``Date``, ``HomeTeam``,
        ``AwayTeam``.  Bookmaker odds columns are optional but improve
        predictions.

    Returns
    -------
    list[dict]
        One dict per fixture with keys: ``home_team``, ``away_team``,
        ``date``, ``prediction``, ``prob_home``, ``prob_draw``,
        ``prob_away``.
    """
    data_cfg = config["data"]
    feature_cfg = config.get("features", {})
    output_cfg = config["output"]

    # Load trained model
    model_path = Path(output_cfg["model_path"])
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found: {model_path}.  Run 'train' first."
        )
    model = joblib.load(model_path)

    # Load historical data
    df = load_matches(
        csv_path=data_cfg.get("csv_path"), csv_glob=data_cfg.get("csv_glob")
    )

    # Build prediction DataFrame
    if isinstance(fixtures, list):
        pred_df = _build_fixture_df(fixtures)
    else:
        pred_df = fixtures.copy()

    n_pred = len(pred_df)
    if n_pred == 0:
        return []

    # Build features – prediction rows are frozen (no stat updates)
    feat, _target = build_features(
        df,
        prediction_df=pred_df,
        **_feature_kwargs(feature_cfg),
    )

    # Extract only the prediction rows (last n_pred rows)
    pred_features = feat.iloc[-n_pred:].copy()
    pred_features = _drop_metadata_columns(pred_features)

    # Predict
    predictions = model.predict(pred_features)

    # Probabilities (if model supports it)
    try:
        probas = model.predict_proba(pred_features)
        class_labels = list(model.classes_)
    except Exception:
        probas = None
        class_labels = None

    # Build result dicts
    results: list[dict] = []
    for i in range(n_pred):
        home = str(pred_df.iloc[i].get("HomeTeam", "?"))
        away = str(pred_df.iloc[i].get("AwayTeam", "?"))
        date = str(pred_df.iloc[i].get("Date", "?"))
        pred_label = str(predictions[i])

        result: dict = {
            "date": date,
            "home_team": home,
            "away_team": away,
            "prediction": pred_label,
        }

        if probas is not None and class_labels is not None:
            for cls, prob in zip(class_labels, probas[i]):
                if str(cls) == "H" or str(cls) == "1":
                    result["prob_home"] = float(prob)
                elif str(cls) == "D":
                    result["prob_draw"] = float(prob)
                elif str(cls) == "A" or str(cls) == "0":
                    result["prob_away"] = float(prob)

        results.append(result)

    return results


def print_predictions(results: list[dict]) -> None:
    """Pretty-print prediction results to stdout."""
    label_map = {"H": "HOME WIN", "D": "DRAW", "A": "AWAY WIN"}

    for r in results:
        home = r["home_team"]
        away = r["away_team"]
        date = r["date"]
        pred = label_map.get(r["prediction"], r["prediction"])

        print(f"\n{'=' * 55}")
        print(f"  {home} vs {away}")
        print(f"  {date}")
        print(f"{'=' * 55}")

        if "prob_home" in r:
            ph = r["prob_home"] * 100
            pd_ = r["prob_draw"] * 100
            pa = r["prob_away"] * 100

            bar_h = "█" * int(ph / 2)
            bar_d = "█" * int(pd_ / 2)
            bar_a = "█" * int(pa / 2)

            print(f"  Home win:  {ph:5.1f}%  {bar_h}")
            print(f"  Draw:      {pd_:5.1f}%  {bar_d}")
            print(f"  Away win:  {pa:5.1f}%  {bar_a}")

        print(f"  → Prediction: {pred}")
        print()
