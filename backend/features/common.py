import numpy as np
import pandas as pd


def compute_performance_raw(df: pd.DataFrame) -> pd.DataFrame:
    """performance_raw = (likes+comments+shares+saves) / reach, per PRD.
    Rows with zero/NULL reach can't produce a ratio and are dropped."""
    engagement = df[["likes", "comments", "shares", "saves"]].fillna(0).sum(axis=1)
    reach = df["reach"].replace(0, np.nan)
    df = df.assign(performance_raw=engagement / reach)
    return df.dropna(subset=["performance_raw"])