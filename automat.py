#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import pandas as pd
import numpy as np
import sys
import time

# ---------- HELPERY ----------

def _norm(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "").replace("\xa0", "").replace("\t", "")

def _trim(val):
    if pd.isna(val): return ""
    s = str(val)
    if ";" in s: s = s.split(";", 1)[0].strip()
    return s

def _float(x):
    if pd.isna(x): return None
    s = str(x)
    for u in ["m²", "m2", "zł/m²", "zł/m2", "zł"]:
        s = s.replace(u, "")
    s = s.replace(" ", "").replace(",", ".").replace("\xa0","")
    s = "".join(ch for ch in s if (ch.isdigit() or ch == "." or ch == "-"))
    try:
        return float(s) if s else None
    except:
        return None

def _find(cols, names):
    norm = { _norm(c): c for c in cols }
    for n in names:
        k=_norm(n)
        if k in norm: return norm[k]
    for c in cols:
        if any(_norm(n) in _norm(c) for n in names): return c
    return None

# ---------- ALGORYTM AUTOMAT ----------

def run_automat(xlsx_path: Path, base_dir: Path, margin_pct: float, margin_m2: float):
    """Wczytuje raport i automatycznie przelicza WSZYSTKIE wiersze.
       Nie tworzy plików (Nr KW).xlsx.
       Tylko wpisuje wartości do raportu.
    """

    # ---- Wczytaj raport ----
    if xlsx_path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(xlsx_path)
    else:
        df = pd.read_csv(xlsx_path, sep=None, engine="python")

    # ---- Wczytaj Polska.xlsx ----
    pl_path = base_dir / "Polska.xlsx"
    if not pl_path.exists():
        raise FileNotFoundError(f"Brak {pl_path}")

    df_pl = pd.read_excel(pl_path)

    # znajdź kolumny w Polsce
    col_area_pl  = _find(df_pl.columns, ["metry","powierzchnia","m2","obszar"])
    col_price_pl = _find(df_pl.columns, ["cena_za_metr","cena za metr","cena za m2","cena/m2"])
    if not col_area_pl or not col_price_pl:
        raise ValueError("Brak kolumn metrażu lub ceny w Polska.xlsx")

    # ---- kolumny wynikowe (utwórz jeśli brak) ----
    C1="Średnia cena za m2 ( z bazy)"
    C2="Średnia skorygowana cena za m2"
    C3="Statystyczna wartość nieruchomości"
    for c in (C1,C2,C3):
        if c not in df.columns: df[c] = ""

    # ---- Iteracja po wierszach raportu ----
    for i in range(len(df)):
        row = df.iloc[i]

        # Metraż
        col_area = _find(df.columns, ["Obszar","metry","powierzchnia"])
        val_area = _float(_trim(row[col_area])) if col_area else None
        if val_area is None:  # brak metrażu => puste wartości
            df.at[i,C1]="" ; df.at[i,C2]="" ; df.at[i,C3]=""
            continue

        # lokalizacja
        def get(cands):
            c=_find(df.columns,cands)
            return _trim(row[c]) if c else ""

        woj_r=get(["Województwo","woj"])
        pow_r=get(["Powiat"])
        gmi_r=get(["Gmina"])
        mia_r=get(["Miejscowość","Miasto"])
        dzl_r=get(["Dzielnica","Osiedle"])
        uli_r=get(["Ulica","Ulica(dla budynku)","Ulica(dla lokalu)"])

        # ---- filtr metrażu (tylko ± m2) ----
        delta = abs(margin_m2)
        lo,hi = max(0,val_area-delta), val_area+delta
        A = df_pl[col_area_pl].map(_float)
        mask = (A>=lo)&(A<=hi)

        def eq(col_names,val):
            c=_find(df_pl.columns,col_names)
            if not c or not str(val).strip(): return pd.Series(True,index=df_pl.index)
            s=df_pl[c].astype(str).str.strip().str.lower()
            return s==str(val).strip().lower()

        # pełne dopasowanie
        mask &= eq(["wojewodztwo","województwo"],woj_r)
        mask &= eq(["powiat"],pow_r)
        mask &= eq(["gmina"],gmi_r)
        mask &= eq(["miejscowosc","miasto","miejscowość"],mia_r)
        if dzl_r: mask &= eq(["dzielnica","osiedle"],dzl_r)
        if uli_r: mask &= eq(["ulica"],uli_r)
        sel=df_pl[mask].copy()

        # fallback ulica→dzielnica→miasto, dzielnica→miasto, samo miasto
        if sel.empty and uli_r:
            m= (A>=lo)&(A<=hi)
            m &= eq(["wojewodztwo","województwo"],woj_r)
            m &= eq(["miejscowosc","miasto","miejscowość"],mia_r)
            if dzl_r: m &= eq(["dzielnica","osiedle"],dzl_r)
            m &= eq(["ulica"],uli_r)
            sel=df_pl[m].copy()
        if sel.empty and dzl_r:
            m=(A>=lo)&(A<=hi)
            m &= eq(["wojewodztwo","województwo"],woj_r)
            m &= eq(["miejscowosc","miasto","miejscowość"],mia_r)
            m &= eq(["dzielnica","osiedle"],dzl_r)
            sel=df_pl[m].copy()
        if sel.empty and mia_r:
            m=(A>=lo)&(A<=hi)
            m &= eq(["wojewodztwo","województwo"],woj_r)
            m &= eq(["miejscowosc","miasto","miejscowość"],mia_r)
            sel=df_pl[m].copy()

        if sel.empty:
            df.at[i,C1]="" ; df.at[i,C2]="" ; df.at[i,C3]=""
            continue

        # IQR remove
        P = sel[col_price_pl].map(_float)
        sel = sel[P.notna()].copy()
        P = sel[col_price_pl].map(_float)
        if len(P)>=4:
            q1=np.nanpercentile(P,25)
            q3=np.nanpercentile(P,75)
            lo2=q1-1.5*(q3-q1)
            hi2=q3+1.5*(q3-q1)
            sel=sel[(P>=lo2)&(P<=hi2)]
            P=sel[col_price_pl].map(_float)

        # ---- średnia + skorygowana + wartość ----
        avg=float(np.nanmean(P)) if len(P)>0 else None
        if avg is not None and margin_pct>0:
            corr= avg*(1-margin_pct/100)
        else:
            corr=avg
        val = (val_area*corr) if (val_area and corr) else ""

        df.at[i,C1]= avg if avg else ""
        df.at[i,C2]= corr if corr else ""
        df.at[i,C3]= val if val else ""

    # ---- zapisz raport ----
    if xlsx_path.suffix.lower() in (".xlsx",".xls"):
        df.to_excel(xlsx_path, index=False)
    else:
        df.to_csv(xlsx_path, index=False, encoding="utf-8-sig")


# ---------- START ----------

if __name__=="__main__":
    # args: path_to_report, base_folder, margin_pct, margin_m2
    if len(sys.argv)<5:
        print("Użycie: Automat <plik_raportu> <folder_baza> <obnizka_%> <+-m2>")
        sys.exit(1)

    raport=Path(sys.argv[1])
    folder=Path(sys.argv[2])
    pct=float(sys.argv[3])
    m2=float(sys.argv[4])

    t=time.time()
    run_automat(raport, folder, pct, m2)
    print(f"[OK] Zakończono w {time.time()-t:.2f}s")
