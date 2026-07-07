# Premier League Predictor

Starter ML workspace for training baseline models to predict match result:
- `H` = home win
- `D` = draw
- `A` = away win

## Quick Start

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -e .[dev]
```

3. Train a model:

```bash
pl-predictor train --config configs/default.yaml
```

4. Evaluate a trained model:

```bash
pl-predictor evaluate --config configs/default.yaml
```

## Data Format

Input CSV should contain these columns:
- `Date`
- `HomeTeam`
- `AwayTeam`
- `FTHG` (full time home goals)
- `FTAG` (full time away goals)
- `FTR` (full time result: `H`, `D`, `A`)

The default config loads all season files from `data/raw/*.csv`.

Training now uses pre-match features only:
- team historical points/goals per game before kickoff
- home vs away team identity
- weekend indicator
- optional bookmaker implied probabilities when `B365H/B365D/B365A` are present

By default, training uses a chronological split so the final 20% of matches are used as a future-style validation set.

## Project Layout

- `src/premier_league_predictor/`: source code
- `configs/default.yaml`: training configuration
- `data/raw/`: raw input data
- `models/`: saved trained models
- `tests/`: unit tests
