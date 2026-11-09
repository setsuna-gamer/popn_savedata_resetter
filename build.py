"""PyInstaller でこの OS 向けのネイティブ実行ファイルをビルドする。

    pip install pyinstaller
    python build.py

dist/ に popn_savedata_resetter_gui (GUI) と popn_savedata_resetter_cli (CLI) が出力される。
PyInstaller はクロスコンパイルできないため、各 OS 上で実行すること
(GitHub Actions: .github/workflows/build.yml)。
"""
import subprocess
import sys

COMMON = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile"]

subprocess.check_call(COMMON + ["--windowed", "--name", "popn_savedata_resetter_gui", "popn_gui.py"])
subprocess.check_call(COMMON + ["--name", "popn_savedata_resetter_cli", "popn_tool.py"])
