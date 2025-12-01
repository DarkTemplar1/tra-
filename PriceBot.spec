# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
from pathlib import Path

# główny plik startowy EXE
entry_script = 'launcher_gui.py'

# folder modules musi być kopiowany obok EXE
datas = [
    ('modules', 'modules'),
    ('teryt.csv', '.'),
    ('obszar_sadow.xlsx', '.'),
    ('Słownik do Pricebota .xlsx', '.'),
]

a = Analysis(
    [entry_script],
    pathex=['.'],
    binaries=[],
    datas=datas,

    hiddenimports=[
        # tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',

        # biblioteki wymagane przez projekt
        'pandas',
        'numpy',
        'openpyxl',
        'requests',
        'bs4',
        'lxml',

        # Twoje moduły
        'adres_otodom',
        'automaty',
        'bazadanych',
        'bootstrap_files',
        'CzyszczenieAdresu',
        'czyszczeniebazydanych',
        'jeden_właściciel',
        'jeden_właściciel_i_LOKAL_MIESZKALNY',
        'kolumny',
        'linki_mieszkania',
        'LOKAL_MIESZKALNY',
        'scalanie',
        'scraper_otodom',
        'scraper_otodom_mieszkania',
        'selektor_csv',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='PriceBot',
    debug=False,
    strip=False,
    upx=False,
    console=False
)
