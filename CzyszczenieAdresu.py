#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CzyszczenieAdresu.py

Uzupełnia luki w kolumnach adresowych raportu PriceBota na podstawie TERYT (teryt.csv).

Działa na kolumnach:
- Województwo
- Powiat
- Gmina
- Miejscowość
- Dzielnica

Tylko uzupełnia brakujące wartości – NIC nie zmienia tam, gdzie coś już jest.
Zapisuje wynik DO TEGO SAMEGO PLIKU, który podasz w argumencie.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import unicodedata
import pandas as pd


ADDR_COLS = ["Województwo", "Powiat", "Gmina", "Miejscowość", "Dzielnica"]


# ---------- Normalizacja tekstu (bez ogonków, małe litery, 1 spacja) ----------

def _norm(s: str) -> str:
    s = str(s or "").strip().lower()
    s = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(ch)
    )
    while "  " in s:
        s = s.replace("  ", " ")
    return s


# ---------- Wczytanie i przygotowanie TERYT ----------

def load_teryt(teryt_path: str = "teryt.csv") -> pd.DataFrame:
    """
    Wczytuje teryt.csv (Wojewodztwo;Powiat;Gmina;Miejscowosc;Dzielnica;...)
    i dodaje kolumny znormalizowane do dopasowań.
    """
    p = Path(teryt_path)
    if not p.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku TERYT: {p}")

    df = pd.read_csv(p, sep=";", dtype=str).fillna("")

    required = ["Wojewodztwo", "Powiat", "Gmina", "Miejscowosc", "Dzielnica"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Brak kolumny '{col}' w pliku TERYT")

    df["woj_n"] = df["Wojewodztwo"].map(_norm)
    df["pow_n"] = df["Powiat"].map(_norm)
    df["gmi_n"] = df["Gmina"].map(_norm)
    df["miej_n"] = df["Miejscowosc"].map(_norm)
    df["dz_n"] = df["Dzielnica"].map(_norm)

    return df


# ---------- Uzupełnianie jednego wiersza ----------

def _enrich_row(row: pd.Series, teryt: pd.DataFrame) -> pd.Series:
    """
    Uzupełnia dziury adresowe w jednym wierszu na podstawie TERYT,
    ale tylko wtedy, gdy wynik jest jednoznaczny.
    """
    r = row.copy()

    woj_n = _norm(r["Województwo"]) if r.get("Województwo", "") else ""
    pow_n = _norm(r["Powiat"])       if r.get("Powiat", "")       else ""
    gmi_n = _norm(r["Gmina"])        if r.get("Gmina", "")        else ""
    mj_n  = _norm(r["Miejscowość"])  if r.get("Miejscowość", "")  else ""
    dz_n  = _norm(r["Dzielnica"])    if r.get("Dzielnica", "")    else ""

    subset = teryt

    # 1) zawężamy po województwie
    if woj_n:
        subset = subset[subset["woj_n"] == woj_n]

    # 2) zawężamy po powiecie (ważne np. Puck w powiecie puckim vs kartuskim)
    if pow_n:
        sub = subset[subset["pow_n"] == pow_n]
        if not sub.empty:
            subset = sub

    # 3) dzielnica (dla dużych miast)
    if dz_n:
        sub = subset[subset["dz_n"] == dz_n]
        if not sub.empty:
            subset = sub

    # 4) miejscowość
    if mj_n:
        sub = subset[subset["miej_n"] == mj_n]
        if not sub.empty:
            subset = sub

    # 5) gmina – jeśli już jest w wierszu, jeszcze mocniej zawężamy
    if gmi_n:
        sub = subset[subset["gmi_n"] == gmi_n]
        if not sub.empty:
            subset = sub

    if subset.empty:
        return r

    # Uzupełnij tylko brakujące pola, jeśli w TERYCIE jest dokładnie 1 wartość
    for col in ADDR_COLS:
        if not r.get(col, ""):
            if col == "Województwo":
                t_col = "Wojewodztwo"
            elif col == "Miejscowość":
                t_col = "Miejscowosc"
            else:
                t_col = col

            vals = subset[t_col].unique()
            if len(vals) == 1 and vals[0]:
                r[col] = vals[0]

    return r


# ---------- Przetwarzanie całego pliku ----------

def clean_report(path: Path, teryt_path: str = "teryt.csv") -> None:
    teryt = load_teryt(teryt_path)

    if not path.exists():
        raise FileNotFoundError(f"Plik raportu nie istnieje: {path}")

    # wczytaj raport
    df = pd.read_excel(path).fillna("")

    # upewnij się, że kolumny adresowe istnieją
    for col in ADDR_COLS:
        if col not in df.columns:
            df[col] = ""

    # statystyka przed
    missing_before = (df[ADDR_COLS] == "").sum()

    # uzupełnianie
    df2 = df.apply(_enrich_row, axis=1, teryt=teryt)

    # statystyka po
    missing_after = (df2[ADDR_COLS] == "").sum()

    # zapis NADPISUJĄCY ten sam plik
    df2.to_excel(path, index=False)

    # proste logi na stdout (widać w konsoli / logach)
    print("CzyszczenieAdresu – statystyka braków:")
    print("PRZED:")
    print(missing_before.to_string())
    print("\nPO:")
    print(missing_after.to_string())
    print(f"\nZapisano zmiany w pliku: {path}")


# ---------- CLI ----------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Uzupełnianie braków adresowych w raporcie na podstawie TERYT."
    )
    parser.add_argument(
        "raport",
        help="Ścieżka do pliku raportu .xlsx (w miejscu, które czyta PriceBot).",
    )
    parser.add_argument(
        "--teryt",
        default="teryt.csv",
        help="Ścieżka do pliku teryt.csv (domyślnie ./teryt.csv).",
    )

    args = parser.parse_args(argv)

    raport_path = Path(args.raport).resolve()

    try:
        clean_report(raport_path, teryt_path=args.teryt)
    except Exception as e:
        print(f"[BŁĄD] CzyszczenieAdresu.py: {e}")
        return 1

    print("\n✔ Zakończono pracę: CzyszczenieAdresu.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
