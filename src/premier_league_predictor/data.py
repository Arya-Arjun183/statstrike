from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def _resolve_paths(csv_path: str | Path | None, csv_glob: str | None) -> list[Path]:
    if csv_glob:
        paths = sorted(Path().glob(csv_glob))
        if paths:
            return paths

    if csv_path is None:
        raise ValueError("Either data.csv_path or data.csv_glob must be provided")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return [path]


def _read_csv_with_season(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).copy()  # defragment wide CSVs
    return df.assign(season=path.stem)


def _concat_dataframes(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    merged = pd.concat(frames, ignore_index=True)
    if "Date" in merged.columns:
        merged["Date"] = pd.to_datetime(merged["Date"], dayfirst=True, errors="coerce")
        merged = merged.sort_values("Date").reset_index(drop=True)
    return merged.copy()  # defragment


def load_matches(csv_path: str | Path | None = None, csv_glob: str | None = None) -> pd.DataFrame:
    paths = _resolve_paths(csv_path=csv_path, csv_glob=csv_glob)
    frames = [_read_csv_with_season(path) for path in paths]
    return _concat_dataframes(frames)
