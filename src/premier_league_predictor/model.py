from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from catboost import CatBoostClassifier


class TwoStageDrawClassifier(BaseEstimator, ClassifierMixin):
    """Predict draw vs non-draw first, then home vs away for non-draws."""

    def __init__(self, draw_threshold: float | None = None) -> None:
        self.draw_threshold = draw_threshold
        self.draw_model = LogisticRegression(max_iter=1000, class_weight="balanced")
        self.non_draw_model = LogisticRegression(max_iter=1000, class_weight="balanced")

    def fit(self, x: np.ndarray, y: np.ndarray) -> "TwoStageDrawClassifier":
        y_array = np.asarray(y)
        self.classes_ = np.unique(y_array)
        is_draw = (y_array == "D").astype(int)
        self.draw_model.fit(x, is_draw)

        if self.draw_threshold is None:
            draw_rate = float(is_draw.mean())
            train_draw_prob = self.draw_model.predict_proba(x)[:, 1]
            quantile = max(0.0, min(1.0, 1.0 - draw_rate))
            self.draw_threshold_ = float(np.quantile(train_draw_prob, quantile))
        else:
            self.draw_threshold_ = float(self.draw_threshold)

        non_draw_mask = y_array != "D"
        self.non_draw_model.fit(x[non_draw_mask], y_array[non_draw_mask])
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        draw_prob = self.draw_model.predict_proba(x)[:, 1]
        non_draw_pred = self.non_draw_model.predict(x)
        threshold = getattr(self, "draw_threshold_", self.draw_threshold)
        preds = np.where(draw_prob >= threshold, "D", non_draw_pred)
        return preds


class CatBoostMultiClassClassifier(BaseEstimator, ClassifierMixin):
    """CatBoost multiclass wrapper that handles string labels."""

    def __init__(self) -> None:
        self.model = CatBoostClassifier(
            loss_function="MultiClass",
            iterations=600,
            learning_rate=0.05,
            depth=6,
            l2_leaf_reg=3.0,
            random_seed=42,
            verbose=False,
        )
        self.label_encoder = LabelEncoder()

    def fit(self, x: np.ndarray, y: np.ndarray) -> "CatBoostMultiClassClassifier":
        y_array = np.asarray(y)
        self.label_encoder.fit(y_array)
        encoded_y = self.label_encoder.transform(y_array).ravel()
        self.model.fit(x, encoded_y)
        self.classes_ = self.label_encoder.classes_
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        predicted = self.model.predict(x)
        predicted = np.asarray(predicted).astype(int).ravel()
        return self.label_encoder.inverse_transform(predicted)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)


class StackingEnsembleClassifier(BaseEstimator, ClassifierMixin):
    """Stack several diverse classifiers and learn a final combiner."""

    def __init__(self) -> None:
        self.model = StackingClassifier(
            estimators=[
                ("logreg", LogisticRegression(max_iter=1000)),
                ("rf", RandomForestClassifier(n_estimators=400, random_state=42)),
                (
                    "hgb",
                    HistGradientBoostingClassifier(
                        learning_rate=0.05,
                        max_iter=300,
                        max_depth=5,
                        min_samples_leaf=20,
                        random_state=42,
                    ),
                ),
                ("cat", CatBoostMultiClassClassifier()),
            ],
            final_estimator=LogisticRegression(max_iter=1000),
            stack_method="predict_proba",
            passthrough=False,
            cv=5,
            n_jobs=None,
        )

    def fit(self, x: np.ndarray, y: np.ndarray) -> "StackingEnsembleClassifier":
        self.model.fit(x, y)
        self.classes_ = self.model.classes_
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)


class SoftVotingEnsembleClassifier(BaseEstimator, ClassifierMixin):
    """Soft-voting ensemble that averages predicted probabilities."""

    def __init__(self) -> None:
        self.model = VotingClassifier(
            estimators=[
                ("logreg", LogisticRegression(max_iter=1000)),
                ("rf", RandomForestClassifier(n_estimators=400, random_state=42)),
                (
                    "hgb",
                    HistGradientBoostingClassifier(
                        learning_rate=0.05,
                        max_iter=300,
                        max_depth=5,
                        min_samples_leaf=20,
                        random_state=42,
                    ),
                ),
                ("cat", CatBoostMultiClassClassifier()),
            ],
            voting="soft",
            n_jobs=None,
        )

    def fit(self, x: np.ndarray, y: np.ndarray) -> "SoftVotingEnsembleClassifier":
        self.model.fit(x, y)
        self.classes_ = self.model.classes_
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)


def choose_draw_threshold(
    draw_prob: np.ndarray,
    non_draw_pred: np.ndarray,
    y_true: np.ndarray,
    metric: str = "accuracy",
) -> float:
    y_array = np.asarray(y_true)
    candidate_thresholds = np.unique(np.clip(draw_prob, 0.0, 1.0))
    if candidate_thresholds.size == 0:
        return 0.5

    best_threshold = 0.5
    best_score = -1.0

    for threshold in candidate_thresholds:
        pred = np.where(draw_prob >= threshold, "D", non_draw_pred)
        accuracy = float(np.mean(pred == y_array))

        draw_true = y_array == "D"
        draw_pred = pred == "D"
        tp = float(np.sum(draw_true & draw_pred))
        fp = float(np.sum(~draw_true & draw_pred))
        fn = float(np.sum(draw_true & ~draw_pred))
        precision = 0.0 if (tp + fp) == 0 else tp / (tp + fp)
        recall = 0.0 if (tp + fn) == 0 else tp / (tp + fn)
        draw_f1 = 0.0 if (precision + recall) == 0 else 2.0 * precision * recall / (precision + recall)

        if metric == "draw_f1":
            score = draw_f1
        elif metric == "accuracy":
            score = accuracy
        elif metric == "hybrid":
            score = 0.75 * accuracy + 0.25 * draw_f1
        else:
            raise ValueError("metric must be one of: accuracy, draw_f1, hybrid")

        if score > best_score:
            best_score = score
            best_threshold = float(threshold)

    return best_threshold


_ALGORITHMS = (
    "logistic_regression",
    "logistic_regression_balanced",
    "random_forest",
    "hist_gradient_boosting",
    "two_stage_draw_model",
    "catboost",
    "stacking_ensemble",
    "soft_voting_ensemble",
)


def build_model(
    algorithm: str,
    draw_threshold: float | None = None,
    calibrate: bool = False,
) -> Pipeline:
    """Construct a full sklearn Pipeline (preprocessor + classifier).

    Parameters
    ----------
    algorithm : str
        One of the supported algorithm names.
    draw_threshold : float | None
        Only used when *algorithm* is ``"two_stage_draw_model"``.
    calibrate : bool
        If ``True``, wrap the classifier with ``CalibratedClassifierCV``
        (isotonic, 3-fold).  Ignored for the two-stage draw model.
    """
    numeric_pipeline = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    categorical_pipeline = make_pipeline(
        SimpleImputer(strategy="most_frequent"),
        OneHotEncoder(handle_unknown="ignore", sparse_output=False),
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, make_column_selector(dtype_include="number")),
            ("cat", categorical_pipeline, make_column_selector(dtype_include="object")),
        ]
    )

    if algorithm == "logistic_regression":
        clf = LogisticRegression(max_iter=1000)
    elif algorithm == "logistic_regression_balanced":
        clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    elif algorithm == "two_stage_draw_model":
        clf = TwoStageDrawClassifier(draw_threshold=draw_threshold)
    elif algorithm == "catboost":
        clf = CatBoostMultiClassClassifier()
    elif algorithm == "stacking_ensemble":
        clf = StackingEnsembleClassifier()
    elif algorithm == "soft_voting_ensemble":
        clf = SoftVotingEnsembleClassifier()
    elif algorithm == "hist_gradient_boosting":
        clf = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=300,
            max_depth=5,
            min_samples_leaf=20,
            random_state=42,
        )
    elif algorithm == "random_forest":
        clf = RandomForestClassifier(n_estimators=300, random_state=42)
    else:
        raise ValueError(f"algorithm must be one of: {', '.join(_ALGORITHMS)}")

    # Optional probability calibration (not compatible with two-stage draw model)
    if calibrate and algorithm != "two_stage_draw_model":
        clf = CalibratedClassifierCV(clf, method="isotonic", cv=3)

    return Pipeline(steps=[("prep", preprocessor), ("clf", clf)])
