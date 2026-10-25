"""Forecast accuracy metrics. All inputs/outputs in MW. error = forecast - actual."""
from __future__ import annotations

import numpy as np
import pandas as pd

# MAPE is undefined at zero and explodes near zero; only periods with actual >= this are used.
MAPE_MIN_ACTUAL_MW = 100.0


def compute_metrics(m: pd.DataFrame, mape_min_actual_mw: float = MAPE_MIN_ACTUAL_MW) -> dict:
    n = len(m)
    if n == 0:
        return {"n": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "mape_pct": None,
                "mape_n": 0, "mape_min_actual_mw": mape_min_actual_mw}
    err = m["error_mw"].to_numpy(dtype=float)
    act = m["actual_mw"].to_numpy(dtype=float)
    ok = act >= mape_min_actual_mw
    mape = float(np.mean(np.abs(err[ok]) / act[ok]) * 100) if ok.any() else None
    return {
        "n": n,
        "mae_mw": float(np.mean(np.abs(err))),
        "rmse_mw": float(np.sqrt(np.mean(err ** 2))),
        "bias_mw": float(np.mean(err)),
        "mape_pct": mape,
        "mape_n": int(ok.sum()),
        "mape_min_actual_mw": mape_min_actual_mw,
        "p10_error_mw": float(np.percentile(err, 10)),
        "p90_error_mw": float(np.percentile(err, 90)),
    }
