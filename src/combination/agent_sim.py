"""Stylized agent-based stress test. Synthetic and illustrative, not a market forecast."""
from __future__ import annotations
import numpy as np


def simulate_agents(steps: int = 120, simulations: int = 1000, trend_strength: float = 0.0,
                    macro_shock: float = 0.0, mean_reversion: float = 0.15, seed: int = 7) -> dict:
    if not 10 <= steps <= 1000 or not 100 <= simulations <= 20000:
        raise ValueError('steps debe estar entre 10 y 1000; simulations entre 100 y 20000.')
    if not -3 <= trend_strength <= 3 or not -5 <= macro_shock <= 5 or not 0 <= mean_reversion <= 1:
        raise ValueError('Parámetros fuera de límites.')
    rng = np.random.default_rng(seed)
    # Three abstract populations: trend followers, mean reversion and macro-shock impulse.
    noise = rng.normal(0, 0.01, size=(simulations, steps))
    trend = trend_strength * 0.001
    reversion = np.zeros((simulations, steps))
    path = np.zeros((simulations, steps))
    for t in range(1, steps):
        reversion[:, t] = -mean_reversion * path[:, t-1]
        shock = (macro_shock * 0.001 if t == max(1, steps // 10) else 0.0)
        path[:, t] = path[:, t-1] + trend + reversion[:, t] + noise[:, t] + shock
    terminal = path[:, -1]
    return {'model':'agentes estilizados: seguimiento de tendencia + reversión a la media + shock exógeno',
            'steps': steps, 'simulations': simulations, 'trend_strength': trend_strength,
            'macro_shock': macro_shock, 'mean_reversion': mean_reversion,
            'terminal_return_q05': float(np.quantile(terminal, .05)), 'terminal_return_q50': float(np.quantile(terminal, .5)),
            'terminal_return_q95': float(np.quantile(terminal, .95)), 'fraction_terminal_positive': float((terminal>0).mean()),
            'warning':'Simulación sintética para estrés de supuestos. No está calibrada con agentes reales, no predice precios ni genera probabilidades operativas.'}
