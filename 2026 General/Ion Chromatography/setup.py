"""
Build a standalone macOS .app for the LCD -> CSV converter.

One-time setup:
    pip install py2app

Build:
    python setup.py py2app

The app will appear in ./dist/lcd_to_csv_app.app — drag it to /Applications
or your dock.

For faster iteration while testing, use the alias build (symlinks instead of
copying everything):
    python setup.py py2app -A
"""

import sys
sys.setrecursionlimit(10000)

from setuptools import setup

APP = ["lcd_to_csv_app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "packages": ["olefile", "pandas", "numpy"],
    "includes": ["lcd_to_csv"],
    "excludes": ["zmq", "PyQt5", "PySide2", "PySide6", "PyQt6", "matplotlib", "scipy", "IPython", "jupyter"],
    "plist": {
        "CFBundleName": "LCD to CSV Converter",
        "CFBundleShortVersionString": "1.0.0",
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
