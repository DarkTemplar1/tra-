#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import annotations
from pathlib import Path
import sys
import unicodedata

import numpy as np
import pandas as pd


# --- pomocnicze z selektor_csv ----------------------------------------------

def _norm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "").replace("\xa0", "").replace("\t", "")

def _find_col(cols, candidates):
    norm_map = { _norm(c): c for c in cols }
    # dokładne
    for cand in candidates:
        key = _norm(cand)
        if key in norm_map:
            return norm_map[key]
    # "zawiera"
    for c in cols:
        if any(_norm(x) in _norm(c) for x in candidates):
            return c
    return None

def _trim_after_semicolon(val):
    if pd.isna(val):
        return ""
    s = str(val)
    if ";" in s:
        s = s.split(";", 1)[0].strip()
    return s

def _to_float_maybe(x):
    """Parsuje liczby typu '101,62 m²', '52 m2', '11 999 zł/m²' itd."""
    if pd.isna(x):
        return None
    s = str(x)
    for unit in ["m²", "m2", "zł/m²", "zł/m2", "zł"]:
        s = s.replace(unit, "")
    s = s.replace(" ", "").replace("\xa0", "").replace(",", ".")
    s = "".join(ch for ch in s if (ch.isdigit() or ch == "." or ch == "-"))
    try:
        return float(s) if s else None
    except Exception:
        return None


VALUE_COLS = [
    "Średnia cena za m2 ( z bazy)",
    "Średnia skorygowana cena za m2",
    "Statystyczna wartość nieruchomości",
]


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Użycie: python automat.py <plik_raportu.xlsx> <folder_bazy>", file=sys.stderr)
        return 2

    raport_path = Path(argv[1]).expanduser().resolve()
    base_dir    = Path(argv[2]).expanduser().resolve()
    polska_path = base_dir / "Polska.xlsx"

    if not raport_path.exists():
        print(f"[ERROR] Plik raportu nie istnieje: {raport_path}", file=sys.stderr)
        return 2
    if not polska_path.exists():
        print(f"[ERROR] Nie znaleziono bazy Polska.xlsx w folderze: {base_dir}", file=sys.stderr)
        return 2

    print(f"[INFO] Raport : {raport_path}")
    print(f"[INFO] Baza   : {polska_path}")

    # --- wczytaj raport ---
    if raport_path.suffix.lower() in (".xlsx", ".xls"):
        df_r = pd.read_excel(raport_path)
    else:
        df_r = pd.read_csv(raport_path, sep=None, engine="python")

    # --- wczytaj Polska.xlsx ---
    df_pl = pd.read_excel(polska_path)

    # kolumny w Polska.xlsx
    col_area_pl = _find_col(df_pl.columns, ["metry", "powierzchnia", "m2", "obszar"])
    col_price_pl = _find_col(
        df_pl.columns,
        ["cena_za_metr", "cena za metr", "cena za m²", "cena za m2", "cena/m2"]
    )
    if col_area_pl is None or col_price_pl is None:
        print("[ERROR] Brak kolumn metrażu i/lub ceny za m² w Polska.xlsx", file=sys.stderr)
        return 2

    # mapy kolumn w raporcie
    cols_r = list(df_r.columns)

    kw_col = _find_col(cols_r,
        ["Nr KW", "nr_kw", "nrksiegi", "nr księgi", "nr_ksiegi", "numer księgi"]
    )
    area_col = _find_col(cols_r, ["Obszar", "metry", "powierzchnia"])

    woj_col = _find_col(cols_r, ["Województwo", "wojewodztwo", "woj"])
    pow_col = _find_col(cols_r, ["Powiat"])
    gmi_col = _find_col(cols_r, ["Gmina"])
    mia_col = _find_col(cols_r, ["Miejscowość", "Miejscowosc", "Miasto"])
    dzl_col = _find_col(cols_r, ["Dzielnica", "Osiedle"])
    uli_col = _find_col(cols_r, ["Ulica", "Ulica(dla budynku)", "Ulica(dla lokalu)"])

    # kolumny wynikowe
    col_avg = _find_col(cols_r,
        ["Średnia cena za m2 ( z bazy)", "Srednia cena za m2 ( z bazy)",
         "Średnia cena za m² (z bazy)"]
    )
    col_avg_corr = _find_col(cols_r,
        ["Średnia skorygowana cena za m2", "Srednia skorygowana cena za m2"]
    )
    col_stat = _find_col(cols_r,
        ["Statystyczna wartość nieruchomości", "Statystyczna wartosc nieruchomosci"]
    )

    if col_avg is None:
        col_avg = VALUE_COLS[0];  df_r[col_avg] = ""
    if col_avg_corr is None:
        col_avg_corr = VALUE_COLS[1];  df_r[col_avg_corr] = ""
    if col_stat is None:
        col_stat = VALUE_COLS[2];  df_r[col_stat] = ""

    # parametry (na razie stałe – jak w GUI domyślnie)
    margin_m2  = 15.0
    margin_pct = 15.0

    # ---- pomoc: maski lokalizacji w Polska.xlsx ----
    def _eq_mask(col_candidates, value):
        col = _find_col(df_pl.columns, col_candidates)
        if col is None or not str(value).strip():
            return pd.Series(True, index=df_pl.index)
        s = df_pl[col].astype(str).str.strip().str.lower()
        v = str(value).strip().lower()
        return s == v

    # --- pętla po wierszach raportu ---
    for i in range(len(df_r)):
        row = df_r.iloc[i]

        area_val = _to_float_maybe(_trim_after_semicolon(row[area_col])) if area_col else None
        if area_val is None:
            # brak metrażu – pomijamy wiersz
            continue

        woj_r = _trim_after_semicolon(row[woj_col]) if woj_col else ""
        pow_r = _trim_after_semicolon(row[pow_col]) if pow_col else ""
        gmi_r = _trim_after_semicolon(row[gmi_col]) if gmi_col else ""
        mia_r = _trim_after_semicolon(row[mia_col]) if mia_col else ""
        dzl_r = _trim_after_semicolon(row[dzl_col]) if dzl_col else ""
        uli_r = _trim_after_semicolon(row[uli_col]) if uli_col else ""

        # --- filtr metrażu ---
        delta = abs(margin_m2)
        low, high = max(0.0, area_val - delta), area_val + delta
        m = df_pl[col_area_pl].map(_to_float_maybe)
        mask_area = (m >= low) & (m <= high)

        # pełny filtr
        mask_full = mask_area.copy()
        mask_full &= _eq_mask(["wojewodztwo", "województwo"], woj_r)
        mask_full &= _eq_mask(["powiat"], pow_r)
        mask_full &= _eq_mask(["gmina"], gmi_r)
        mask_full &= _eq_mask(["miejscowosc", "miasto", "miejscowość"], mia_r)
        if dzl_r:
            mask_full &= _eq_mask(["dzielnica", "osiedle"], dzl_r)
        if uli_r:
            mask_full &= _eq_mask(["ulica"], uli_r)

        df_sel = df_pl[mask_full].copy()

        # fallback 1: ulica + dzielnica + miasto
        if df_sel.empty and uli_r:
            mask_ul = mask_area.copy()
            mask_ul &= _eq_mask(["wojewodztwo", "województwo"], woj_r)
            mask_ul &= _eq_mask(["miejscowosc", "miasto", "miejscowość"], mia_r)
            if dzl_r:
                mask_ul &= _eq_mask(["dzielnica", "osiedle"], dzl_r)
            mask_ul &= _eq_mask(["ulica"], uli_r)
            df_sel = df_pl[mask_ul].copy()

        # fallback 2: dzielnica + miasto
        if df_sel.empty and dzl_r:
            mask_dziel = mask_area.copy()
            mask_dziel &= _eq_mask(["wojewodztwo", "województwo"], woj_r)
            mask_dziel &= _eq_mask(["miejscowosc", "miasto", "miejscowość"], mia_r)
            mask_dziel &= _eq_mask(["dzielnica", "osiedle"], dzl_r)
            df_sel = df_pl[mask_dziel].copy()

        # fallback 3: samo miasto
        if df_sel.empty and mia_r:
            mask_miasto = mask_area.copy()
            mask_miasto &= _eq_mask(["wojewodztwo", "województwo"], woj_r)
            mask_miasto &= _eq_mask(["miejscowosc", "miasto", "miejscowość"], mia_r)
            df_sel = df_pl[mask_miasto].copy()

        if df_sel.empty:
            # brak dopasowań – zostawiamy puste pola
            continue

        prices = df_sel[col_price_pl].map(_to_float_maybe)
        df_sel = df_sel[prices.notna()].copy()
        prices = df_sel[col_price_pl].map(_to_float_maybe)

        if len(prices) >= 4:
            q1 = np.nanpercentile(prices, 25)
            q3 = np.nanpercentile(prices, 75)
            iqr = q3 - q1
            lo = q1 - 1.5 * iqr
            hi = q3 + 1.5 * iqr
            df_sel = df_sel[(prices >= lo) & (prices <= hi)].copy()
            prices = df_sel[col_price_pl].map(_to_float_maybe)

        if df_sel.empty:
            continue

        avg = float(np.nanmean(prices)) if not df_sel.empty else None

        if avg is not None and margin_pct > 0:
            corrected = avg * (1 - margin_pct / 100.0)
        else:
            corrected = avg

        stat_val = (area_val * corrected) if (area_val is not None and corrected is not None) else ""

        df_r.at[i, col_avg]       = avg if avg is not None else ""
        df_r.at[i, col_avg_corr]  = corrected if corrected is not None else ""
        df_r.at[i, col_stat]      = stat_val

    # --- zapis raportu w to samo miejsce ---
    try:
        if raport_path.suffix.lower() in (".xlsx", ".xls"):
            df_r.to_excel(raport_path, index=False)
        else:
            df_r.to_csv(raport_path, index=False, encoding="utf-8-sig")
    except PermissionError:
        print(
            f"[ERROR] Nie udało się zapisać raportu (plik może być otwarty w Excelu):\n{raport_path}",
            file=sys.stderr
        )
        return 1
    except Exception as e:
        print(f"[ERROR] Błąd zapisu raportu:\n{raport_path}\n{e}", file=sys.stderr)
        return 1

    print("[OK] Zapisano zmodyfikowany raport.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
