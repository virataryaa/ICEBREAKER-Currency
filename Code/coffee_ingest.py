"""
Coffee Currency Index — ICE Connect Ingest
==========================================
Usage:
    python coffee_ingest.py            # incremental update
    python coffee_ingest.py --full     # full pull from 2014-01-01

Saves to: ../Database/currency_data.parquet
"""

import argparse
import datetime
import logging
import sys
from pathlib import Path

import icepython as ice
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

OUT_FILE   = Path(__file__).parent.parent / "Database" / "currency_data.parquet"
FULL_START = "2014-01-01"

FX_SYMS = {
    "BRL": "BRL@FXP A0-FX",
    "COP": "COP@FXP A0-FX",
    "HNL": "HNL@FXP A0-FX",
    "PEN": "PEN@FXP A0-FX",
    "ETB": "ETB@FXP A0-FX",
    "VND": "VND@FXP A0-FX",
    "IDR": "IDR@FXP A0-FX",
    "UGX": "UGX@FXP A0-FX",
    "INR": "INR@FXP A0-FX",
}

FUTURES_SYMS = {
    "KC_Price": "%KC 2!",
    "RC_Price": "%RC 1!-ICE",
}

ARABICA_WEIGHTS = {
    "BRL": 0.54047,
    "COP": 0.207225,
    "HNL": 0.074291,
    "ETB": 0.119151,
    "PEN": 0.058863,
}

ROBUSTA_WEIGHTS = {
    "VND": 0.47,
    "BRL": 0.11,
    "IDR": 0.17,
    "UGX": 0.16,
    "INR": 0.09,
}

COLUMN_NAMES = {
    "BRL": "Brazil",
    "COP": "Colombia",
    "HNL": "Honduras",
    "PEN": "Peru",
    "ETB": "Ethiopia",
    "VND": "Vietnam",
    "IDR": "Indonesia",
    "UGX": "Uganda",
    "INR": "India",
}


def _fetch_series(sym, field, start, end):
    try:
        data = ice.get_timeseries(sym, [field], granularity='D', start_date=start, end_date=end)
        df = pd.DataFrame(list(data))
        if df.empty or 'Error' in str(df.iloc[0, 0]):
            return pd.Series(dtype=float)
        df.columns = ['Date', 'Val']
        df = df[1:].reset_index(drop=True)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Val'] = pd.to_numeric(df['Val'], errors='coerce')
        return df.set_index('Date')['Val']
    except Exception as e:
        log.warning("fetch failed %s: %s", sym, e)
        return pd.Series(dtype=float)


def fetch_fx(start, end):
    log.info("Fetching FX rates from ICE (%d currencies) from %s", len(FX_SYMS), start)
    frames = {}
    for code, sym in FX_SYMS.items():
        s = _fetch_series(sym, 'Close', start, end)
        if not s.empty:
            frames[code] = s
            log.info("  %s: %d rows", code, s.notna().sum())
        else:
            log.warning("  %s: no data", code)
    return pd.DataFrame(frames)


def fetch_futures(start, end):
    log.info("Fetching futures prices from ICE from %s", start)
    frames = {}
    for col, sym in FUTURES_SYMS.items():
        s = _fetch_series(sym, 'Settle', start, end)
        if not s.empty:
            frames[col] = s
            log.info("  %s (%s): %d rows", col, sym, s.notna().sum())
        else:
            log.warning("  %s: no data", col)
    return pd.DataFrame(frames)


def compute_indices(df):
    out = df.copy().apply(pd.to_numeric, errors='coerce')
    base = {}
    for code in set(list(ARABICA_WEIGHTS) + list(ROBUSTA_WEIGHTS)):
        if code in out.columns:
            s = out[code].dropna()
            base[code] = s.iloc[0] if not s.empty else 1.0

    ara = sum((out[c] / base[c]) * w for c, w in ARABICA_WEIGHTS.items()
              if c in out.columns and c in base) * 100
    rob = sum((out[c] / base[c]) * w for c, w in ROBUSTA_WEIGHTS.items()
              if c in out.columns and c in base) * 100

    out["Arabica_Idx"]    = ara
    out["Robusta_Idx"]    = rob
    out["Spread_Ara_Rob"] = ara - rob
    out = out.rename(columns=COLUMN_NAMES)

    all_cols = list(COLUMN_NAMES.values()) + list(FUTURES_SYMS.keys()) + \
               ["Arabica_Idx", "Robusta_Idx", "Spread_Ara_Rob"]
    existing = [c for c in all_cols if c in out.columns]
    out[existing] = out[existing].ffill()
    return out.reset_index()


def recompute_indices(df):
    out = df.copy()
    col_to_code = {v: k for k, v in COLUMN_NAMES.items()}

    ara_parts, rob_parts = [], []
    for code, w in ARABICA_WEIGHTS.items():
        col = COLUMN_NAMES.get(code)
        if col and col in out.columns:
            s = pd.to_numeric(out[col], errors='coerce')
            base = s.dropna().iloc[0] if not s.dropna().empty else 1.0
            ara_parts.append((s / base) * w)
    for code, w in ROBUSTA_WEIGHTS.items():
        col = COLUMN_NAMES.get(code)
        if col and col in out.columns:
            s = pd.to_numeric(out[col], errors='coerce')
            base = s.dropna().iloc[0] if not s.dropna().empty else 1.0
            rob_parts.append((s / base) * w)

    if ara_parts: out["Arabica_Idx"]    = sum(ara_parts) * 100
    if rob_parts: out["Robusta_Idx"]    = sum(rob_parts) * 100
    if ara_parts and rob_parts:
        out["Spread_Ara_Rob"] = out["Arabica_Idx"] - out["Robusta_Idx"]
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Coffee Currency Ingest | %s", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    if args.full or not OUT_FILE.exists():
        start = FULL_START
        log.info("Mode: FULL from %s", start)
    else:
        existing = pd.read_parquet(OUT_FILE, columns=["Date"])
        latest   = pd.to_datetime(existing["Date"]).max()
        start    = (latest - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
        log.info("Mode: INCREMENTAL from %s", start)

    end = datetime.date.today().isoformat()

    fx_df      = fetch_fx(start, end)
    futures_df = fetch_futures(start, end)

    raw    = fx_df.join(futures_df, how='outer').sort_index().ffill()
    log.info("Rows fetched: %d", len(raw))

    new_df = compute_indices(raw)

    if OUT_FILE.exists() and not args.full:
        old_df = pd.read_parquet(OUT_FILE)
        old_df["Date"] = pd.to_datetime(old_df["Date"])
        new_df["Date"] = pd.to_datetime(new_df["Date"])
        combined = (pd.concat([old_df, new_df])
                    .drop_duplicates(subset=["Date"], keep="last")
                    .sort_values("Date")
                    .reset_index(drop=True))
        combined = recompute_indices(combined)
    else:
        combined = new_df.sort_values("Date").reset_index(drop=True)

    combined["Date"] = pd.to_datetime(combined["Date"])
    combined = combined[combined["Date"] < pd.Timestamp.today().normalize()].reset_index(drop=True)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUT_FILE, engine="pyarrow", index=False)
    log.info("Saved: %s  (%d rows)", OUT_FILE, len(combined))
    log.info("=" * 60)


if __name__ == "__main__":
    main()
