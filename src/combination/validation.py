"""Chronological, leakage-aware descriptive validation of a simple momentum sign baseline."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .data import normalize_ohlc


def evaluate_momentum_baseline(frame: pd.DataFrame, horizon: int = 1, train_fraction: float = .7) -> dict:
    d = normalize_ohlc(frame)
    if horizon < 1 or horizon > 100:
        raise ValueError('El horizonte debe estar entre 1 y 100 velas.')
    close = d.close
    future = close.shift(-horizon) / close - 1
    momentum = close.pct_change(5)
    data = pd.DataFrame({'momentum':momentum, 'future':future}).dropna().reset_index(drop=True)
    split = int(len(data)*train_fraction)
    if split < 30 or len(data)-split < 20:
        raise ValueError('Datos insuficientes: se requieren al menos 50 observaciones válidas tras crear horizonte y separar train/test.')
    train, test = data.iloc[:split], data.iloc[split:]
    # Learn only the direction-specific empirical success rate on training data.
    pred_sign = np.where(test.momentum.to_numpy() >= 0, 1, -1)
    train_sign = np.where(train.momentum.to_numpy() >= 0, 1, -1)
    train_correct = (train_sign * np.sign(train.future.to_numpy()) > 0)
    global_rate = float(train_correct.mean())
    probs = np.empty(len(test), dtype=float)
    for i, sign in enumerate(pred_sign):
        mask = train_sign == sign
        probs[i] = float((train_correct[mask].mean() if mask.any() else global_rate))
    actual_up = (test.future.to_numpy() > 0).astype(float)
    predicted_up = (pred_sign == 1).astype(float)
    realized_correct = (pred_sign * test.future.to_numpy() > 0).astype(float)
    brier = float(np.mean((probs - realized_correct)**2))
    # directional hit rate is more interpretable than the above auxiliary calibration score
    hit = float(np.mean(pred_sign * test.future.to_numpy() > 0))
    return {'method':'momentum 5 velas; corte cronológico sin barajar; tasa de éxito por dirección aprendida solo en train',
            'horizon_bars':horizon,'train_observations':int(len(train)),'test_observations':int(len(test)),
            'train_success_rate':global_rate,'test_directional_hit_rate':hit,
            'train_long_success_rate':float(train_correct[train_sign==1].mean()) if (train_sign==1).any() else None,
            'train_short_success_rate':float(train_correct[train_sign==-1].mean()) if (train_sign==-1).any() else None,
            'test_return_mean':float(test.future.mean()),'test_return_median':float(test.future.median()),
            'probability_note':'Las tasas empíricas son una referencia de entrenamiento, no una probabilidad garantizada. Requiere múltiples ventanas temporales y costes para una evaluación robusta.',
            'brier_auxiliary':brier,'warning':'Baseline de investigación; no incluye costes, slippage, selección múltiple ni estabilidad por régimen.'}
