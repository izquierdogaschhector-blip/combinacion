"""CFTC Commitments of Traders analysis from a user-supplied official CSV export."""
from __future__ import annotations
import pandas as pd


def analyze_cot_csv(frame: pd.DataFrame, contract_search: str = 'GOLD') -> tuple[pd.DataFrame, dict]:
    if frame is None or frame.empty:
        raise ValueError('El CSV COT está vacío.')
    d = frame.copy()
    d.columns = [str(c).strip().lower().replace(' ', '_') for c in d.columns]
    # CFTC CSV exports have inconsistent column names across report families.
    contract_cols = [c for c in d.columns if 'market' in c or 'contract' in c]
    if not contract_cols:
        raise ValueError('No se identifica la columna del contrato/mercado. Descarga un CSV del portal CFTC COT y conserva sus encabezados.')
    contract_col = contract_cols[0]
    mask = d[contract_col].astype(str).str.contains(contract_search, case=False, na=False)
    filt = d.loc[mask].copy()
    if filt.empty:
        examples = ', '.join(d[contract_col].dropna().astype(str).unique()[:8])
        raise ValueError(f'No hay contratos que coincidan con «{contract_search}». Algunos nombres: {examples}')
    date_cols = [c for c in filt.columns if ('report_date' in c or 'as_of' in c or 'report_week' in c or c in ('date','report_date_as_yyyy_mm_dd'))]
    date_col = date_cols[0] if date_cols else None
    if date_col:
        filt[date_col] = pd.to_datetime(filt[date_col], errors='coerce', utc=True)
        filt = filt.sort_values(date_col)
    # Normalize common field names; preserve raw columns for transparent inspection.
    def find_col(words):
        return next((c for c in filt.columns if any(w in c for w in words)), None)
    long_col = find_col(['noncomm_positions_long_all','noncommercial_positions_long_all','noncomm_long_all','noncommercial_long_all','managed_money_positions_long_all','m_money_positions_long_all','m_money_positions_long'])
    short_col = find_col(['noncomm_positions_short_all','noncommercial_positions_short_all','noncomm_short_all','noncommercial_short_all','managed_money_positions_short_all','m_money_positions_short_all','m_money_positions_short'])
    if long_col and short_col:
        filt['net_selected_group'] = pd.to_numeric(filt[long_col], errors='coerce') - pd.to_numeric(filt[short_col], errors='coerce')
        net_col = 'net_selected_group'
    else:
        net_col = None
    summary = {'rows': int(len(filt)), 'contract_column': contract_col, 'contract_search': contract_search,
               'date_column': date_col, 'net_position_column': net_col, 'net_position_definition': 'neto del grupo no comercial o managed money, según columnas presentes' if net_col else None,
               'latest_contract': str(filt[contract_col].iloc[-1]),
               'note': 'COT es posicionamiento semanal de futuros/opciones, no Order Flow intradía ni posicionamiento completo de spot XAUUSD.'}
    if net_col:
        vals = filt[net_col].dropna()
        if not vals.empty:
            summary.update({'latest_net_position': float(vals.iloc[-1]), 'prior_net_position': float(vals.iloc[-2]) if len(vals)>1 else None,
                            'change_net_position': float(vals.iloc[-1]-vals.iloc[-2]) if len(vals)>1 else None,
                            'position_group_type': 'noncommercial' if long_col and ('noncomm' in long_col or 'noncommercial' in long_col) else 'managed_money'})
    return filt, summary


CFTC_DATASETS = {
    'Disaggregated — Futures Only': '72hh-3qpy',
    'Disaggregated — Futures + Options': 'kh3c-gbw2',
    'Legacy — Futures Only': '6dca-aqww',
    'Legacy — Futures + Options': 'jun7-fc8e',
    'Traders in Financial Futures — Futures Only': 'gpe5-46if',
    'Traders in Financial Futures — Futures + Options': 'yw9f-hn96',
}


def fetch_cot_api(dataset_id: str = '72hh-3qpy', contract_search: str = 'GOLD', limit: int = 500) -> pd.DataFrame:
    """Fetch recent CFTC Public Reporting Environment records via its public Socrata endpoint."""
    import requests
    if dataset_id not in set(CFTC_DATASETS.values()):
        raise ValueError('Dataset CFTC no reconocido. Selecciona uno de los informes incluidos.')
    if not 1 <= int(limit) <= 5000:
        raise ValueError('El límite debe estar entre 1 y 5000 filas.')
    search = (contract_search or '').strip()
    if not search or len(search) > 80 or any(ch in search for ch in "'\";"):
        raise ValueError('Texto de contrato vacío o no válido.')
    url = f'https://publicreporting.cftc.gov/resource/{dataset_id}.json'
    params = {'$where': f"upper(market_and_exchange_names) like '%{search.upper()}%'", '$order':'report_date_as_yyyy_mm_dd DESC', '$limit':int(limit)}
    try:
        response = requests.get(url, params=params, timeout=(5, 30), headers={'User-Agent':'CombinacionMaestra/5.0 (personal research app)'})
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f'No se pudo consultar CFTC Public Reporting API: {exc}') from exc
    except ValueError as exc:
        raise RuntimeError('La API de CFTC devolvió una respuesta que no es JSON válido.') from exc
    if not isinstance(payload, list):
        raise RuntimeError(f'Respuesta inesperada de CFTC: {str(payload)[:400]}')
    if not payload:
        raise RuntimeError(f'CFTC no devolvió filas para el filtro {search!r}; prueba GOLD o revisa el informe elegido.')
    return pd.DataFrame(payload)
