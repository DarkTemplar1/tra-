#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CzyszczenieAdresu.py

Uzupełnia luki w kolumnach adresowych raportu PriceBota
na podstawie:
- TERYT (teryt.csv)
- obszar_sadow.xlsx (zakresy sądów, też z kolumnami adresowymi)

Zakładamy, że BRAKI w adresie są oznaczone jako:
    ---    (trzy myślniki)
lub zostawione puste.

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
import math


ADDR_COLS = ["Województwo", "Powiat", "Gmina", "Miejscowość", "Dzielnica"]

# kolumny wartości, w których wpisujemy komunikat jeśli adresu nie da się dopełnić
VALUE_COLS = [
    "Średnia cena za m2 ( z bazy)",
    "Średnia skorygowana cena za m2",
    "Statystyczna wartość nieruchomości",
]

# słowa typu "Kolonia", "Osiedle", "Nowa", "Stara" – ignorujemy przy dopasowaniu miejscowości/gminy
PLACE_GENERIC_WORDS = {
    "kolonia", "kol.", "osiedle", "os.", "nowa", "stara"
}


# ---------- Helpery ----------

def _norm(s: str) -> str:
    """Normalizacja do dopasowań (bez ogonków, małe litery, jedna spacja)."""
    s = str(s or "").strip().lower()
    s = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(ch)
    )
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def _place_base(s: str) -> str:
    """
    Uproszczony klucz nazwy miejscowości/gminy do porównań:
    - normalizacja jak w _norm (bez ogonków, małe litery),
    - wyrzucamy "kolonia", "osiedle", "nowa", "stara" itp.
    """
    s_norm = _norm(s)
    if not s_norm:
        return ""
    words = [w for w in s_norm.split() if w not in PLACE_GENERIC_WORDS]
    return " ".join(words) if words else s_norm


def _is_missing(v) -> bool:
    """
    Czy traktujemy to jako 'brak wartości'?

    Brak = puste, NaN, '---'.
    """
    if v is None:
        return True
    if isinstance(v, float):
        try:
            if math.isnan(v):
                return True
        except Exception:
            pass

    s = str(v).strip()
    return s == "" or s == "---"


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

    # klucze "bazowe" (bez Kolonia/Osiedle/Nowa/Stara) dla miejscowości/gminy
    df["miej_base"] = df["Miejscowosc"].map(_place_base)
    df["gmi_base"] = df["Gmina"].map(_place_base)

    return df


# ---------- Wczytanie obszaru sądów ----------

def load_obszar_sadow(path: str = "obszar_sadow.xlsx") -> pd.DataFrame:
    """
    Wczytuje obszar_sadow.xlsx (Oznaczenie sądu, Sąd rejonowy,
    Województwo, Powiat, Gmina, Miejscowość, Dzielnica)
    i dodaje kolumny znormalizowane do dopasowań.
    """
    p = Path(path)
    if not p.exists():
        # Nie traktujemy tego jako krytyczny błąd – po prostu nie używamy pliku sądów.
        print(f"[INFO] Nie znaleziono {p}, używam tylko TERYT.")
        return pd.DataFrame(columns=[
            "Województwo", "Powiat", "Gmina", "Miejscowość", "Dzielnica",
            "woj_n", "pow_n", "gmi_n", "miej_n", "dz_n",
            "miej_base", "gmi_base"
        ])

    df = pd.read_excel(p, sheet_name=0, dtype=str).fillna("")

    required = ["Województwo", "Powiat", "Gmina", "Miejscowość", "Dzielnica"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Brak kolumny '{col}' w pliku obszar_sadow.xlsx")

    df["woj_n"] = df["Województwo"].map(_norm)
    df["pow_n"] = df["Powiat"].map(_norm)
    df["gmi_n"] = df["Gmina"].map(_norm)
    df["miej_n"] = df["Miejscowość"].map(_norm)
    df["dz_n"] = df["Dzielnica"].map(_norm)

    df["miej_base"] = df["Miejscowość"].map(_place_base)
    df["gmi_base"] = df["Gmina"].map(_place_base)

    return df


# ---------- Uzupełnianie na podstawie jednej bazy (TERYT / obszar_sadow) ----------

def _fill_from_source(
    r: pd.Series,
    df: pd.DataFrame,
    woj_n: str,
    pow_n: str,
    gmi_n: str,
    mj_n: str,
    dz_n: str,
) -> pd.Series:
    """
    Uzupełnia braki w wierszu `r` na podstawie jednego źródła (TERYT albo obszar_sadow).
    Wprowadzone heurystyki:
    - używamy też kluczy bazowych miejscowości/gminy (bez Kolonia/Osiedle/Nowa/Stara),
    - jeśli jest Gmina, ale brak Miejscowości → próbujemy podstawić miejscowość
      "domyślną" (najczęstsza dla danej gminy),
    - nadal uzupełniamy tylko pola, które są puste lub '---'.
    """
    if df.empty:
        return r

    subset = df.copy()

    # 1) Województwo
    if woj_n:
        subset = subset[subset["woj_n"] == woj_n]

    # 2) Powiat
    if pow_n and not subset.empty:
        sub = subset[subset["pow_n"] == pow_n]
        if not sub.empty:
            subset = sub

    # Klucze bazowe z wiersza (dla dopisków typu "Kolonia", "Nowa", "Stara")
    mj_base = _place_base(r.get("Miejscowość", "")) if not _is_missing(r.get("Miejscowość", "")) else ""
    gmi_base_row = _place_base(r.get("Gmina", "")) if not _is_missing(r.get("Gmina", "")) else ""

    # 3) Dzielnica (jeśli jest)
    if dz_n and not subset.empty:
        sub = subset[subset["dz_n"] == dz_n]
        if not sub.empty:
            subset = sub

    # 4) Miejscowość: najpierw normalna, potem bazowa (bez Kolonia/Osiedle/Nowa/Stara)
    if (mj_n or mj_base) and not subset.empty:
        sub = subset
        if mj_n:
            sub = sub[sub["miej_n"] == mj_n]
        if sub.empty and mj_base and "miej_base" in subset.columns:
            sub = subset[subset["miej_base"] == mj_base]
        if not sub.empty:
            subset = sub

    # 5) Gmina: normalna + bazowa
    if (gmi_n or gmi_base_row) and not subset.empty:
        sub = subset
        if gmi_n:
            sub = sub[sub["gmi_n"] == gmi_n]
        if sub.empty and gmi_base_row and "gmi_base" in subset.columns:
            sub = subset[subset["gmi_base"] == gmi_base_row]
        if not sub.empty:
            subset = sub

    if subset.empty:
        return r

    # 5a) SPECJALNIE: jeśli mamy Gminę, ale brak Miejscowości → spróbuj ustalić "stolicę gminy"
    if _is_missing(r.get("Miejscowość", "")) and not _is_missing(r.get("Gmina", "")):
        if "Miejscowość" in subset.columns:
            mcol = "Miejscowość"
        else:
            mcol = "Miejscowosc"
        if mcol in subset.columns and not subset.empty:
            mode_vals = subset[mcol].mode()
            if not mode_vals.empty:
                r["Miejscowość"] = mode_vals.iloc[0]

    # 6) Uzupełniamy tylko brakujące pola (puste lub '---'),
    #    ale TYLKO jeżeli w źródle jest dokładnie jedna wartość.
    for col in ADDR_COLS:
        cur = r.get(col, "")
        if _is_missing(cur):
            if col == "Województwo":
                t_col = "Województwo" if "Województwo" in subset.columns else "Wojewodztwo"
            elif col == "Miejscowość":
                t_col = "Miejscowość" if "Miejscowość" in subset.columns else "Miejscowosc"
            else:
                t_col = col

            if t_col not in subset.columns:
                continue

            vals = subset[t_col].dropna().unique()
            if len(vals) == 1 and vals[0]:
                r[col] = vals[0]

    return r


# ---------- Uzupełnianie jednego wiersza – TERYT + obszar_sadow ----------

def _enrich_row(row: pd.Series, teryt: pd.DataFrame, sad: pd.DataFrame) -> pd.Series:
    """
    Uzupełnia dziury adresowe w jednym wierszu na podstawie:
    1) TERYT
    2) obszar_sadow.xlsx (jako dodatkowe źródło)

    Brak = puste albo '---'.
    """
    r = row.copy()

    woj_raw = r.get("Województwo", "")
    pow_raw = r.get("Powiat", "")
    gmi_raw = r.get("Gmina", "")
    mj_raw  = r.get("Miejscowość", "")
    dz_raw  = r.get("Dzielnica", "")

    woj_n = _norm(woj_raw) if not _is_missing(woj_raw) else ""
    pow_n = _norm(pow_raw) if not _is_missing(pow_raw) else ""
    gmi_n = _norm(gmi_raw) if not _is_missing(gmi_raw) else ""
    mj_n  = _norm(mj_raw)  if not _is_missing(mj_raw)  else ""
    dz_n  = _norm(dz_raw)  if not _is_missing(dz_raw)  else ""

    # najpierw próbujemy TERYT
    r = _fill_from_source(r, teryt, woj_n, pow_n, gmi_n, mj_n, dz_n)

    # jeśli nadal są braki – próbujemy obszar_sadow.xlsx
    if not sad.empty and any(_is_missing(r.get(col, "")) for col in ADDR_COLS):
        r = _fill_from_source(r, sad, woj_n, pow_n, gmi_n, mj_n, dz_n)

    return r


# ---------- Przetwarzanie całego pliku ----------

def clean_report(path: Path, teryt_path: str = "teryt.csv", sad_path: str = "obszar_sadow.xlsx") -> None:
    teryt = load_teryt(teryt_path)
    sad = load_obszar_sadow(sad_path)

    if not path.exists():
        raise FileNotFoundError(f"Plik raportu nie istnieje: {path}")

    # wczytaj raport
    df = pd.read_excel(path).fillna("")

    # upewnij się, że kolumny adresowe istnieją
    for col in ADDR_COLS:
        if col not in df.columns:
            df[col] = ""

    # Zamień wszystkie '---' w kolumnach adresowych na puste stringi
    # (żeby wewnętrznie traktować to jak brak)
    for col in ADDR_COLS:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda v: "" if _is_missing(v) else v
            )

    # statystyka przed (brak = puste lub '---')
    missing_before = (df[ADDR_COLS].applymap(_is_missing)).sum()

    # uzupełnianie (TERYT + obszar_sadow)
    df2 = df.apply(_enrich_row, axis=1, teryt=teryt, sad=sad)

    # --- NOWOŚĆ: jeśli po uzupełnianiu nadal są braki w adresie,
    #             to w kolumnach VALUE_COLS wpisujemy komunikat
    #             "Proszę dopisz manualnie".
    # najpierw upewniamy się, że kolumny wartości istnieją
    for vcol in VALUE_COLS:
        if vcol not in df2.columns:
            df2[vcol] = ""

    # wiersze, gdzie nadal brakuje czegokolwiek w adresie
    unresolved_mask = df2[ADDR_COLS].applymap(_is_missing).any(axis=1)
    df2.loc[unresolved_mask, VALUE_COLS] = "Proszę dopisz manualnie"

    # wszystko na WIELKIE LITERY (z zachowaniem polskich znaków) dla adresu
    for col in ADDR_COLS:
        if col in df2.columns:
            df2[col] = df2[col].astype(str).str.upper()

    # statystyka po
    missing_after = (df2[ADDR_COLS].applymap(_is_missing)).sum()

    # zapis NADPISUJĄCY ten sam plik
    df2.to_excel(path, index=False)

    # proste logi na stdout (widać w konsoli / logach)
    print("CzyszczenieAdresu – statystyka braków (brak = puste lub '---'):")
    print("PRZED:")
    print(missing_before.to_string())
    print("\nPO:")
    print(missing_after.to_string())
    print(f"\nZapisano zmiany w pliku: {path}")


# ---------- CLI ----------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Uzupełnianie braków adresowych w raporcie na podstawie TERYT + obszar_sadow.xlsx."
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
    parser.add_argument(
        "--obszar",
        default="obszar_sadow.xlsx",
        help="Ścieżka do pliku obszar_sadow.xlsx (domyślnie ./obszar_sadow.xlsx).",
    )

    args = parser.parse_args(argv)

    raport_path = Path(args.raport).resolve()

    try:
        clean_report(raport_path, teryt_path=args.teryt, sad_path=args.obszar)
    except Exception as e:
        print(f"[BŁĄD] CzyszczenieAdresu.py: {e}")
        return 1

    print("\n✔ Zakończono pracę: CzyszczenieAdresu.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
