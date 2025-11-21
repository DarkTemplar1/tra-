#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scalanie wszystkich CSV z linków Otodom w jedną bazę województwa.
Poprawia pola rozbite przez przecinek (np.: cena 123900,90 → 1 pole).
Przyjmuje, że poprawny rekord ma 15 kolumn:

cena, cena_za_metr, metry, liczba_pokoi, pietro, rynek, rok_budowy, material,
wojewodztwo, powiat, gmina, miejscowosc, dzielnica, ulica, link
"""

import pandas as pd
from pathlib import Path

# 👇 OCZEKIWANY UKŁAD CSV
HEADERS = [
    "cena", "cena_za_metr", "metry", "liczba_pokoi", "pietro", "rynek", "rok_budowy",
    "material", "wojewodztwo", "powiat", "gmina", "miejscowosc", "dzielnica", "ulica", "link"
]

EXPECTED_COLS = 15


def log(msg: str):
    print(msg)


def read_csvs(in_dir: Path, pattern: str = "*.csv", encoding="utf-8") -> list[pd.DataFrame]:
    """Czyta wszystkie CSV, scalając błędne pola (np. przecinki w cenie → 16 kolumn)."""
    files = sorted(in_dir.glob(pattern))
    dfs: list[pd.DataFrame] = []

    if not files:
        log(f"[WARN] Brak plików CSV w {in_dir}")
        return []

    for f in files:
        try:
            log(f"[READ] {f.name}")
            df = pd.read_csv(f, encoding=encoding, dtype=str, na_filter=False)

            if df.shape[1] == EXPECTED_COLS + 1:
                log(f"[FIX] Scalanie pola ceny (rozbita na 2 kolumny) → {f.name}")
                df.iloc[:, 0] = df.iloc[:, 0].astype(str) + "," + df.iloc[:, 1].astype(str)
                df = df.drop(df.columns[1], axis=1)

            if df.shape[1] > EXPECTED_COLS:
                log(f"[FIX] Przycinanie dodatkowych kolumn w {f.name}")
                df = df.iloc[:, :EXPECTED_COLS]

            for col in HEADERS:
                if col not in df.columns:
                    df[col] = ""

            df = df[HEADERS]

            woj = f.stem.lower().replace(".__tmp__", "").replace("_", "")
            mask = df["wojewodztwo"].astype(str).str.strip().eq("")
            if mask.any():
                df.loc[mask, "wojewodztwo"] = woj

            dfs.append(df)

        except Exception as e:
            log(f"[ERR] Błąd odczytu {f}: {e}")

    return dfs


def merge_to_excel(in_dir: str, out_file: str, encoding="utf-8"):
    """Scal CSV i zapisz do pliku Excel."""
    in_dir = Path(in_dir)
    dfs = read_csvs(in_dir, "*.csv", encoding)

    if not dfs:
        log("[EXIT] Brak danych do scalenia.")
        return

    full_df = pd.concat(dfs, ignore_index=True)
    full_df.to_excel(out_file, index=False)
    log(f"[OK] Zapisano w: {out_file}")


if __name__ == "__main__":
    # 🔧 PODAJ ŚCIEŻKĘ DO FOLDERU CSV ORAZ NAZWĘ WYJŚCIOWEGO .xlsx
    merge_to_excel("linki", "Polska.xlsx")
