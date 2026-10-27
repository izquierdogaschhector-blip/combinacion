"""Descriptive statistics, bootstrap scenarios and simple out-of-sample checks."""
import numpy as np
import pandas as pd
from .data import normalize_ohlc


def summarize_returns(frame: pd.DataFrame) -> dict:
    d = normalize_ohlc(frame)
    r = d.close.pct_change().dropna()
    if len(r) < 20:
        raise ValueError("Se necesitan al menos 21 velas para estadísticas de retornos.")
    return {
        "n_returns": int(len(r)),
        "mean_return": float(r.mean()),
        "median_return": float(r.median()),
        "std_return": float(r.std(ddof=1)),
        "min_return": float(r.min()), "max_return": float(r.max()),
        "positive_fraction": float((r > 0).mean()),
        "skew": float(r.skew()), "kurtosis": float(r.kurtosis()),
        "max_drawdown_close_to_close": float((d.close / d.close.cummax() - 1).min()),
    }


def bootstrap_terminal_returns(frame: pd.DataFrame, horizon: int = 10, simulations: int = 2000, seed: int = 42) -> dict:
    d = normalize_ohlc(frame)
    returns = d.close.pct_change().dropna().to_numpy()
    if len(returns) < 30:
        raise ValueError("Se necesitan al menos 30 retornos para bootstrap.")
    if horizon < 1 or simulations < 100:
        raise ValueError("horizon debe ser >=1 y simulations >=100.")
    rng = np.random.default_rng(seed)
    sampled = rng.choice(returns, size=(simulations, horizon), replace=True)
    terminal = np.prod(1 + sampled, axis=1) - 1
    return {
        "method": "bootstrap i.i.d. de retornos históricos; no modela cambios de régimen ni dependencia serial",
        "horizon_bars": int(horizon), "simulations": int(simulations),
        "q05": float(np.quantile(terminal, .05)), "q25": float(np.quantile(terminal, .25)),
        "q50": float(np.quantile(terminal, .50)), "q75": float(np.quantile(terminal, .75)),
        "q95": float(np.quantile(terminal, .95)),
        "prob_positive_in_sample_resampling": float((terminal > 0).mean()),
    }


def simple_walk_forward(frame: pd.DataFrame, train_fraction: float = 0.7) -> dict:
    """Transparent baseline: train/test split, reports direction of mean return only."""
    d = normalize_ohlc(frame)
    r = d.close.pct_change().dropna()
    split = int(len(r) * train_fraction)
    if split < 20 or len(r) - split < 10:
        raise ValueError("Datos insuficientes para una separación train/test.")
    train, test = r.iloc[:split], r.iloc[split:]
    predicted_direction = 1 if train.mean() >= 0 else -1
    realized = test * predicted_direction
    return {
        "train_bars": int(len(train)), "test_bars": int(len(test)),
        "train_mean_return": float(train.mean()), "test_mean_return": float(test.mean()),
        "baseline_direction": "long bias" if predicted_direction == 1 else "short bias",
        "test_directional_hit_rate": float((realized > 0).mean()),
        "note": "Baseline ingenuo, no estrategia operativa; no incorpora costes, slippage ni selección de parámetros.",
    }
