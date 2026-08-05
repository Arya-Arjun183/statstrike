from __future__ import annotations

import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, log_loss

from premier_league_predictor.data import load_matches
from premier_league_predictor.features import build_features
from premier_league_predictor.model import build_model, choose_draw_threshold


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
    "include_xg_actual",
)


def _feature_kwargs(feature_cfg: dict) -> dict[str, bool]:
    """Extract feature-flag keyword arguments from the config."""
    return {k: bool(feature_cfg.get(k, True)) for k in _FEATURE_FLAG_KEYS}


def _calculate_sample_weights(seasons_series, decay_rate: float) -> np.ndarray:
    if decay_rate >= 1.0:
        return np.ones(len(seasons_series))
    
    def extract_year(s):
        try:
            parts = str(s).split('-')
            for p in parts:
                if p.isdigit():
                    return int(p)
            return 0
        except (ValueError, AttributeError):
            return 0

    years = seasons_series.apply(extract_year)
    max_year = years.max()
    gaps = max_year - years
    weights = decay_rate ** gaps
    return weights.values


def _drop_metadata_columns(x):
    """Remove internal metadata columns before training."""
    to_drop = [c for c in ("_season",) if c in x.columns]
    return x.drop(columns=to_drop) if to_drop else x


def _has_predict_proba(pipeline) -> bool:
    """Check whether the pipeline's final estimator supports predict_proba."""
    clf = pipeline.named_steps.get("clf")
    return hasattr(clf, "predict_proba") or hasattr(clf, "predict_proba")


def _compute_log_loss(pipeline, x_test, y_test, labels) -> float | None:
    """Return log-loss if the model supports probability predictions."""
    try:
        proba = pipeline.predict_proba(x_test)
        return float(log_loss(y_test, proba, labels=labels))
    except Exception:
        return None


# ------------------------------------------------------------------
# Walk-forward season-by-season backtesting
# ------------------------------------------------------------------

def _walk_forward_train(config: dict) -> dict:
    """Train with walk-forward validation across seasons.

    For each test season from the 3rd available season onwards, train on
    all preceding seasons and evaluate on the test season.  Finally, train
    a model on *all* pre-holdout seasons and evaluate on the holdout.
    """
    data_cfg = config["data"]
    feature_cfg = config.get("features", {})
    train_cfg = config["training"]
    output_cfg = config["output"]
    fw_kwargs = _feature_kwargs(feature_cfg)

    algorithm = train_cfg.get("algorithm", "stacking_ensemble")
    calibrate = bool(train_cfg.get("calibrate", False))
    holdout_season = train_cfg.get("holdout_season")

    # Load all data and build features in one pass (features accumulate
    # correctly because _build_pre_match_stats iterates chronologically).
    df = load_matches(csv_path=data_cfg.get("csv_path"), csv_glob=data_cfg.get("csv_glob"))
    x, y = build_features(df, **fw_kwargs)

    exclude_seasons = data_cfg.get("exclude_seasons", [])
    if exclude_seasons and "_season" in x.columns:
        keep_mask = ~x["_season"].isin(exclude_seasons)
        x = x.loc[keep_mask]
        y = y.loc[keep_mask]

    if data_cfg.get("target_type") == "binary_home_win":
        y = (y == "H").astype(int)

    if "_season" not in x.columns:
        raise ValueError("Walk-forward requires a 'season' column in the data. "
                         "Use csv_glob to load multiple season files.")

    seasons = x["_season"].copy()
    x_clean = _drop_metadata_columns(x)
    unique_seasons = list(seasons.unique())  # already chronological

    if holdout_season is None:
        holdout_season = unique_seasons[-1]
    if holdout_season not in unique_seasons:
        raise ValueError(f"Holdout season '{holdout_season}' not found in data.")

    cv_seasons = [s for s in unique_seasons if s != holdout_season]
    labels = sorted(y.unique())

    # --- Cross-validation folds ---
    per_season: list[dict] = []
    min_train_seasons = 2
    for i in range(min_train_seasons, len(cv_seasons)):
        train_seasons = set(cv_seasons[:i])
        test_season = cv_seasons[i]

        train_mask = seasons.isin(train_seasons)
        test_mask = seasons == test_season

        x_tr = x_clean.loc[train_mask]
        y_tr = y.loc[train_mask]
        x_te = x_clean.loc[test_mask]
        y_te = y.loc[test_mask]
        
        train_seasons_tr = seasons.loc[train_mask]
        decay_rate = float(train_cfg.get("season_decay_rate", 1.0))
        fit_params = {}
        if decay_rate < 1.0:
            fit_params["clf__sample_weight"] = _calculate_sample_weights(train_seasons_tr, decay_rate)

        pipe = build_model(algorithm, calibrate=calibrate, dixon_coles_target=data_cfg.get("target_type", "dixon_coles_xg"))
        pipe.fit(x_tr, y_tr, **fit_params)

        preds = pipe.predict(x_te)
        acc = float(accuracy_score(y_te, preds))
        ll = _compute_log_loss(pipe, x_te, y_te, labels)

        per_season.append({
            "season": test_season,
            "accuracy": acc,
            "log_loss": ll,
            "n_matches": int(len(y_te)),
        })
        ll_str = f"  log_loss={ll:.4f}" if ll is not None else ""
        print(f"  CV fold {test_season}: accuracy={acc:.4f}{ll_str}  (n={len(y_te)})")

    # --- Final model on all CV seasons, holdout evaluation ---
    train_mask = seasons.isin(set(cv_seasons))
    holdout_mask = seasons == holdout_season

    x_train_final = x_clean.loc[train_mask]
    y_train_final = y.loc[train_mask]
    x_holdout = x_clean.loc[holdout_mask]
    y_holdout = y.loc[holdout_mask]
    
    train_seasons_final = seasons.loc[train_mask]
    decay_rate = float(train_cfg.get("season_decay_rate", 1.0))
    fit_params_final = {}
    if decay_rate < 1.0:
        fit_params_final["clf__sample_weight"] = _calculate_sample_weights(train_seasons_final, decay_rate)

    pipeline = build_model(algorithm, calibrate=calibrate, dixon_coles_target=data_cfg.get("target_type", "dixon_coles_xg"))
    pipeline.fit(x_train_final, y_train_final, **fit_params_final)

    holdout_preds = pipeline.predict(x_holdout)
    holdout_acc = float(accuracy_score(y_holdout, holdout_preds))
    holdout_ll = _compute_log_loss(pipeline, x_holdout, y_holdout, labels)

    # Persist model
    model_path = Path(output_cfg["model_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)

    print(f"\n=== Holdout season {holdout_season} ===")
    print(classification_report(y_holdout, holdout_preds))

    result: dict = {
        "accuracy": holdout_acc,
        "walk_forward_cv": per_season,
    }
    if holdout_ll is not None:
        result["log_loss"] = holdout_ll
    return result


# ------------------------------------------------------------------
# Simple single-split training (original behaviour)
# ------------------------------------------------------------------

def _simple_train(config: dict) -> dict:
    """Original single chronological-or-random split training."""
    data_cfg = config["data"]
    feature_cfg = config.get("features", {})
    train_cfg = config["training"]
    output_cfg = config["output"]
    tuning_cfg = train_cfg.get("tuning", {})
    fw_kwargs = _feature_kwargs(feature_cfg)

    algorithm = train_cfg.get("algorithm", "stacking_ensemble")
    calibrate = bool(train_cfg.get("calibrate", False))

    df = load_matches(csv_path=data_cfg.get("csv_path"), csv_glob=data_cfg.get("csv_glob"))
    x, y = build_features(df, **fw_kwargs)
    
    exclude_seasons = data_cfg.get("exclude_seasons", [])
    if exclude_seasons and "_season" in x.columns:
        keep_mask = ~x["_season"].isin(exclude_seasons)
        x = x.loc[keep_mask]
        y = y.loc[keep_mask]

    if data_cfg.get("target_type") == "binary_home_win":
        y = (y == "H").astype(int)
        
    seasons = x["_season"].copy() if "_season" in x.columns else None
    x = _drop_metadata_columns(x)

    test_size = float(train_cfg.get("test_size", 0.2))
    split_strategy = str(train_cfg.get("split_strategy", "chronological"))

    if split_strategy == "chronological":
        split_idx = int(len(x) * (1.0 - test_size))
        split_idx = max(1, min(split_idx, len(x) - 1))
        x_train, x_test = x.iloc[:split_idx], x.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        seasons_train = seasons.iloc[:split_idx] if seasons is not None else None
    else:
        from sklearn.model_selection import train_test_split

        eval_y_full = _get_eval_y(y)
        n_classes = int(eval_y_full.nunique())
        requested_test_rows = math.ceil(len(y) * test_size)
        stratify_target = eval_y_full if requested_test_rows >= n_classes else None
        
        if seasons is not None:
            x_train, x_test, y_train, y_test, seasons_train, _ = train_test_split(
                x,
                y,
                seasons,
                test_size=test_size,
                random_state=int(train_cfg.get("random_state", 42)),
                stratify=stratify_target,
            )
        else:
            x_train, x_test, y_train, y_test = train_test_split(
                x,
                y,
                test_size=test_size,
                random_state=int(train_cfg.get("random_state", 42)),
                stratify=stratify_target,
            )
            seasons_train = None

    decay_rate = float(train_cfg.get("season_decay_rate", 1.0))
    fit_params = {}
    if decay_rate < 1.0 and seasons_train is not None:
        fit_params["clf__sample_weight"] = _calculate_sample_weights(seasons_train, decay_rate)

    if algorithm == "two_stage_draw_model":
        validation_fraction = float(tuning_cfg.get("validation_fraction", 0.2))
        validation_split_idx = int(len(x_train) * (1.0 - validation_fraction))
        validation_split_idx = max(1, min(validation_split_idx, len(x_train) - 1))
        x_subtrain = x_train.iloc[:validation_split_idx]
        y_subtrain = y_train.iloc[:validation_split_idx]
        x_val = x_train.iloc[validation_split_idx:]
        y_val = y_train.iloc[validation_split_idx:]

        probe_pipeline = build_model(algorithm, dixon_coles_target=data_cfg.get("target_type", "dixon_coles_xg"))
        
        probe_fit_params = {}
        if "clf__sample_weight" in fit_params:
            probe_fit_params["clf__sample_weight"] = fit_params["clf__sample_weight"][:validation_split_idx]
            
        probe_pipeline.fit(x_subtrain, y_subtrain, **probe_fit_params)

        val_features = probe_pipeline.named_steps["prep"].transform(x_val)
        clf = probe_pipeline.named_steps["clf"]
        draw_prob = clf.draw_model.predict_proba(val_features)[:, 1]
        non_draw_pred = clf.non_draw_model.predict(val_features)

        threshold_metric = str(tuning_cfg.get("metric", "accuracy"))
        tuned_threshold = choose_draw_threshold(
            draw_prob, non_draw_pred, np.asarray(y_val), metric=threshold_metric
        )
        print(f"tuned_draw_threshold={tuned_threshold:.4f} metric={threshold_metric}")

        pipeline = build_model(algorithm, draw_threshold=tuned_threshold, dixon_coles_target=data_cfg.get("target_type", "dixon_coles_xg"))
    else:
        pipeline = build_model(algorithm, calibrate=calibrate, dixon_coles_target=data_cfg.get("target_type", "dixon_coles_xg"))

    pipeline.fit(x_train, y_train, **fit_params)

    predictions = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    model_path = Path(output_cfg["model_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)

    print(classification_report(y_test, predictions))

    labels = sorted(y.unique())
    result: dict = {"accuracy": float(accuracy)}
    ll = _compute_log_loss(pipeline, x_test, y_test, labels)
    if ll is not None:
        result["log_loss"] = ll
    return result


# ------------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------------

def train_from_config(config: dict) -> dict:
    """Dispatch to walk-forward or simple training based on config."""
    train_cfg = config.get("training", {})
    if train_cfg.get("walk_forward", False):
        return _walk_forward_train(config)
    return _simple_train(config)
