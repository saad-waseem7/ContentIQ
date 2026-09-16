import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import uuid
import numpy as np
import pandas as pd

from ml.evaluate import spearman_within_user


def test_spearman_within_user_excludes_small_groups():
    small_user = uuid.uuid4()
    large_user = uuid.uuid4()
    df = pd.DataFrame({
        "user_id": [small_user] * 2 + [large_user] * 5,
        "actual": [1, 2] + [1, 2, 3, 4, 5],
        "predicted": [1, 2] + [1, 2, 3, 4, 5],
    })
    rho = spearman_within_user(df, "actual", "predicted", min_rows=3)
    assert abs(rho - 1.0) < 1e-9  # only large_user (perfect correlation) counted; small_user excluded


def test_spearman_within_user_all_groups_too_small_returns_nan():
    df = pd.DataFrame({"user_id": [uuid.uuid4()] * 2, "actual": [1, 2], "predicted": [2, 1]})
    rho = spearman_within_user(df, "actual", "predicted", min_rows=3)
    assert np.isnan(rho)