from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin, clone
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
import pandas as pd
from catboost import CatBoostClassifier


class TargetDropper(BaseEstimator, TransformerMixin):
    """Drop target columns before passing data to ML models to prevent leakage."""
    def fit(self, X, y=None):
        return self
    def transform(self, X):
        return X.drop(columns=["FTHG", "FTAG", "HXG", "AXG"], errors="ignore")


class DixonColesClassifier(BaseEstimator, ClassifierMixin):
    """Dixon-Coles Poisson model for predicting football matches."""

    def __init__(self, target_type="dixon_coles_actual") -> None:
        self.target_type = target_type

    def fit(self, x: np.ndarray | pd.DataFrame, y: np.ndarray | pd.DataFrame, sample_weight: np.ndarray | None = None) -> "DixonColesClassifier":
        if isinstance(x, np.ndarray):
            raise ValueError("DixonColesClassifier requires a DataFrame with 'home_team' and 'away_team' columns.")
        
        if self.target_type == "dixon_coles_actual":
            y_home = np.asarray(x["FTHG"])
            y_away = np.asarray(x["FTAG"])
            self.use_rho = True
        elif self.target_type in ("dixon_coles_xg", "dixon_coles_xg_efficient"):
            y_home = np.asarray(x["HXG"])
            y_away = np.asarray(x["AXG"])
            self.use_rho = False
        else:
            raise ValueError(f"Unsupported target_type for DixonColes: {self.target_type}")

        self.teams_ = np.unique(np.concatenate([x["home_team"].unique(), x["away_team"].unique()]))
        self.team_to_idx_ = {team: i for i, team in enumerate(self.teams_)}
        n_teams = len(self.teams_)
        
        home_idx = np.array([self.team_to_idx_[t] for t in x["home_team"]])
        away_idx = np.array([self.team_to_idx_[t] for t in x["away_team"]])
        
        def log_likelihood(params):
            attack = params[:n_teams]
            defense = params[n_teams:2*n_teams]
            home_adv = params[2*n_teams]
            rho = params[2*n_teams+1] if self.use_rho else 0.0

            lambda_home = np.exp(attack[home_idx] + defense[away_idx] + home_adv)
            lambda_away = np.exp(attack[away_idx] + defense[home_idx])
            
            ll_h = y_home * np.log(lambda_home) - lambda_home
            ll_a = y_away * np.log(lambda_away) - lambda_away
            ll = ll_h + ll_a
            
            if self.use_rho and rho != 0.0:
                tau = np.ones_like(ll)
                m00 = (y_home == 0) & (y_away == 0)
                m01 = (y_home == 0) & (y_away == 1)
                m10 = (y_home == 1) & (y_away == 0)
                m11 = (y_home == 1) & (y_away == 1)
                
                tau[m00] = 1 - lambda_home[m00] * lambda_away[m00] * rho
                tau[m01] = 1 + lambda_home[m01] * rho
                tau[m10] = 1 + lambda_away[m10] * rho
                tau[m11] = 1 - rho
                
                tau = np.clip(tau, 1e-10, None)
                ll += np.log(tau)
                
            if sample_weight is not None:
                ll = ll * sample_weight
                
            penalty = 1000 * (np.mean(attack) - 1.0)**2
            return -np.sum(ll) + penalty

        x0 = np.ones(2 * n_teams + 2)
        x0[:n_teams] = 1.0
        x0[n_teams:2*n_teams] = -1.0
        x0[2*n_teams] = 0.2
        x0[2*n_teams+1] = 0.0

        bounds = [(None, None)] * (2 * n_teams) + [(None, None), (-0.5, 0.5)]
        
        res = minimize(log_likelihood, x0, bounds=bounds, method='L-BFGS-B')
        
        self.params_ = res.x
        self.attack_ = self.params_[:n_teams]
        self.defense_ = self.params_[n_teams:2*n_teams]
        self.home_adv_ = self.params_[2*n_teams]
        self.rho_ = self.params_[2*n_teams+1] if self.use_rho else 0.0
        
        if self.target_type == "dixon_coles_xg_efficient":
            act_home = np.asarray(x["FTHG"])
            act_away = np.asarray(x["FTAG"])
            self.efficiency_ = np.ones(n_teams)
            for i in range(n_teams):
                h_mask = (home_idx == i)
                a_mask = (away_idx == i)
                w_h = sample_weight[h_mask] if sample_weight is not None else np.ones(np.sum(h_mask))
                w_a = sample_weight[a_mask] if sample_weight is not None else np.ones(np.sum(a_mask))
                
                act_goals = np.sum(act_home[h_mask] * w_h) + np.sum(act_away[a_mask] * w_a)
                xg_goals = np.sum(y_home[h_mask] * w_h) + np.sum(y_away[a_mask] * w_a)
                
                self.efficiency_[i] = (act_goals + 1.0) / (xg_goals + 1.0)
        
        self.classes_ = np.array(["A", "D", "H"])
        return self

    def predict_proba(self, x: np.ndarray | pd.DataFrame) -> np.ndarray:
        if isinstance(x, np.ndarray):
            raise ValueError("DixonColesClassifier requires a DataFrame with 'home_team' and 'away_team' columns.")

        home_idx = np.array([self.team_to_idx_.get(t, -1) for t in x["home_team"]])
        away_idx = np.array([self.team_to_idx_.get(t, -1) for t in x["away_team"]])
        
        mean_attack = np.mean(self.attack_)
        mean_defense = np.mean(self.defense_)
        
        h_attack = np.where(home_idx >= 0, self.attack_[home_idx], mean_attack)
        a_defense = np.where(away_idx >= 0, self.defense_[away_idx], mean_defense)
        a_attack = np.where(away_idx >= 0, self.attack_[away_idx], mean_attack)
        h_defense = np.where(home_idx >= 0, self.defense_[home_idx], mean_defense)
        
        lambda_home = np.exp(h_attack + a_defense + self.home_adv_)
        lambda_away = np.exp(a_attack + h_defense)
        
        if self.target_type == "dixon_coles_xg_efficient":
            h_eff = np.where(home_idx >= 0, self.efficiency_[home_idx], 1.0)
            a_eff = np.where(away_idx >= 0, self.efficiency_[away_idx], 1.0)
            lambda_home *= h_eff
            lambda_away *= a_eff
        
        max_goals = 10
        probs = np.zeros((len(x), 3))
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
                if self.use_rho and self.rho_ != 0:
                    if h == 0 and a == 0:
                        p *= np.maximum(1e-10, 1 - lambda_home * lambda_away * self.rho_)
                    elif h == 0 and a == 1:
                        p *= np.maximum(1e-10, 1 + lambda_home * self.rho_)
                    elif h == 1 and a == 0:
                        p *= np.maximum(1e-10, 1 + lambda_away * self.rho_)
                    elif h == 1 and a == 1:
                        p *= np.maximum(1e-10, 1 - self.rho_)
                        
                if h < a:
                    probs[:, 0] += p
                elif h == a:
                    probs[:, 1] += p
                else:
                    probs[:, 2] += p
                
        probs /= probs.sum(axis=1, keepdims=True)
        return probs

    def predict(self, x: np.ndarray | pd.DataFrame) -> np.ndarray:
        proba = self.predict_proba(x)
        return self.classes_[np.argmax(proba, axis=1)]


class TwoStageDrawClassifier(BaseEstimator, ClassifierMixin):
    """Predict draw vs non-draw first, then home vs away for non-draws."""

    def __init__(self, draw_threshold: float | None = None) -> None:
        self.draw_threshold = draw_threshold
        self.draw_model = LogisticRegression(max_iter=1000, class_weight="balanced")
        self.non_draw_model = LogisticRegression(max_iter=1000, class_weight="balanced")

    def fit(self, x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray | None = None) -> "TwoStageDrawClassifier":
        y_array = np.asarray(y)
        self.classes_ = np.unique(y_array)
        is_draw = (y_array == "D").astype(int)
        self.draw_model.fit(x, is_draw, sample_weight=sample_weight)

        if self.draw_threshold is None:
            draw_rate = float(np.average(is_draw, weights=sample_weight) if sample_weight is not None else is_draw.mean())
            train_draw_prob = self.draw_model.predict_proba(x)[:, 1]
            quantile = max(0.0, min(1.0, 1.0 - draw_rate))
            self.draw_threshold_ = float(np.quantile(train_draw_prob, quantile))
        else:
            self.draw_threshold_ = float(self.draw_threshold)

        non_draw_mask = y_array != "D"
        sub_weights = sample_weight[non_draw_mask] if sample_weight is not None else None
        self.non_draw_model.fit(x[non_draw_mask], y_array[non_draw_mask], sample_weight=sub_weights)
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
            auto_class_weights="Balanced",
        )
        self.label_encoder = LabelEncoder()

    def fit(self, x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray | None = None) -> "CatBoostMultiClassClassifier":
        y_array = np.asarray(y)
        self.label_encoder.fit(y_array)
        encoded_y = self.label_encoder.transform(y_array).ravel()
        if sample_weight is not None:
            self.model.fit(x, encoded_y, sample_weight=sample_weight)
        else:
            self.model.fit(x, encoded_y)
        self.classes_ = self.label_encoder.classes_
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        predicted = self.model.predict(x)
        predicted = np.asarray(predicted).astype(int).ravel()
        return self.label_encoder.inverse_transform(predicted)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)


class PipelineWithWeight(BaseEstimator, ClassifierMixin):
    """Wrapper to route sample_weight correctly through a pipeline."""
    def __init__(self, drop, prep, clf):
        self.drop = drop
        self.prep = prep
        self.clf = clf

    def fit(self, X, y, sample_weight=None):
        self.pipe_ = Pipeline([("drop", clone(self.drop)), ("prep", clone(self.prep)), ("clf", clone(self.clf))])
        fit_params = {}
        if sample_weight is not None:
            fit_params["clf__sample_weight"] = sample_weight
        self.pipe_.fit(X, y, **fit_params)
        self.classes_ = self.pipe_.classes_
        return self

    def predict(self, X):
        return self.pipe_.predict(X)

    def predict_proba(self, X):
        return self.pipe_.predict_proba(X)


class StackingEnsembleClassifier(BaseEstimator, ClassifierMixin):
    """Stack several diverse classifiers and learn a final combiner."""

    def __init__(self, base_prep=None, dixon_coles_target="dixon_coles_xg") -> None:
        prep_step = "passthrough" if base_prep is None else clone(base_prep)
        
        def _make_pipe(clf):
            prep = clone(prep_step) if prep_step != "passthrough" else prep_step
            return PipelineWithWeight(TargetDropper(), prep, clf)
            
        self.model = StackingClassifier(
            estimators=[
                ("logreg", _make_pipe(LogisticRegression(max_iter=1000, class_weight="balanced"))),
                ("rf", _make_pipe(RandomForestClassifier(n_estimators=400, random_state=42, class_weight="balanced"))),
                (
                    "hgb",
                    _make_pipe(HistGradientBoostingClassifier(
                        learning_rate=0.05,
                        max_iter=300,
                        max_depth=5,
                        min_samples_leaf=20,
                        random_state=42,
                    )),
                ),
                ("cat", _make_pipe(CatBoostMultiClassClassifier())),
                ("dixon_coles", DixonColesClassifier(target_type=dixon_coles_target)),
            ],
            final_estimator=LogisticRegression(max_iter=1000, class_weight="balanced"),
            stack_method="predict_proba",
            passthrough=False,
            cv=5,
            n_jobs=None,
        )

    def fit(self, x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray | None = None) -> "StackingEnsembleClassifier":
        if sample_weight is not None:
            self.model.fit(x, y, sample_weight=sample_weight)
        else:
            self.model.fit(x, y)
        self.classes_ = self.model.classes_
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x)

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)


class SoftVotingEnsembleClassifier(BaseEstimator, ClassifierMixin):
    """Soft-voting ensemble that averages predicted probabilities."""

    def __init__(self, base_prep=None, dixon_coles_target="dixon_coles_xg") -> None:
        prep_step = "passthrough" if base_prep is None else clone(base_prep)
        
        def _make_pipe(clf):
            prep = clone(prep_step) if prep_step != "passthrough" else prep_step
            return PipelineWithWeight(TargetDropper(), prep, clf)
            
        self.model = VotingClassifier(
            estimators=[
                ("logreg", _make_pipe(LogisticRegression(max_iter=1000))),
                ("rf", _make_pipe(RandomForestClassifier(n_estimators=400, random_state=42))),
                (
                    "hgb",
                    _make_pipe(HistGradientBoostingClassifier(
                        learning_rate=0.05,
                        max_iter=300,
                        max_depth=5,
                        min_samples_leaf=20,
                        random_state=42,
                    )),
                ),
                ("cat", _make_pipe(CatBoostMultiClassClassifier())),
                ("dixon_coles", DixonColesClassifier(target_type=dixon_coles_target)),
            ],
            voting="soft",
            n_jobs=None,
        )

    def fit(self, x: np.ndarray, y: np.ndarray, sample_weight: np.ndarray | None = None) -> "SoftVotingEnsembleClassifier":
        if sample_weight is not None:
            self.model.fit(x, y, sample_weight=sample_weight)
        else:
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
    "dixon_coles_actual",
    "dixon_coles_xg",
    "dixon_coles_xg_efficient",
)


def build_model(
    algorithm: str,
    draw_threshold: float | None = None,
    calibrate: bool = False,
    dixon_coles_target: str = "dixon_coles_xg",
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
    if algorithm in ("dixon_coles_actual", "dixon_coles_xg", "dixon_coles_xg_efficient"):
        return Pipeline(steps=[("clf", DixonColesClassifier(target_type=algorithm))])

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
        clf = StackingEnsembleClassifier(base_prep=preprocessor, dixon_coles_target=dixon_coles_target)
        return Pipeline(steps=[("clf", clf)])
    elif algorithm == "soft_voting_ensemble":
        clf = SoftVotingEnsembleClassifier(base_prep=preprocessor, dixon_coles_target=dixon_coles_target)
        return Pipeline(steps=[("clf", clf)])
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

    return Pipeline(steps=[("drop", TargetDropper()), ("prep", preprocessor), ("clf", clf)])
