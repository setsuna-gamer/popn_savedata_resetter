"""popn_tool.py の GUI 版 (tkinter)。  起動: python popn_gui.py"""
import contextlib
import io
import os
import sys
import threading
import tkinter as tk
from argparse import Namespace
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popn_tool as pt  # noqa: E402

KEEP_CHOICES = {"既定": None, "プレイ回数+クリア印": "plays,extra", "プレイ回数のみ": "plays",
                "クリア印のみ": "extra", "なし (全消去)": "none"}


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=10)
        self.pack(fill="both", expand=True)
        root.title("pop'n music セーブデータツール")
        root.geometry("760x560")

        self.card = tk.StringVar()
        self.dry = tk.BooleanVar(value=True)

        # カード選択
        row = ttk.Frame(self); row.pack(fill="x")
        ttk.Label(row, text="メモリーカード:").pack(side="left")
        ttk.Entry(row, textvariable=self.card).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(row, text="参照...", command=self.browse).pack(side="left")
        ttk.Button(row, text="情報表示", command=self.do_info).pack(side="left", padx=(5, 0))

        ttk.Checkbutton(self, text="ドライラン (書き込まず確認のみ)", variable=self.dry).pack(anchor="w", pady=5)

        nb = ttk.Notebook(self); nb.pack(fill="x")
        games = ["all"] + list(pt.PROFILES)

        # リセット
        t = ttk.Frame(nb, padding=10); nb.add(t, text="レコードリセット")
        self.r_game = self.combo(t, "対象:", games, 0, "popn12")
        self.r_keep = self.combo(t, "残す情報:", list(KEEP_CHOICES), 1, "既定")
        ttk.Button(t, text="実行", command=self.do_reset).grid(row=2, column=1, sticky="w", pady=8)

        # プレイ回数
        t = ttk.Frame(nb, padding=10); nb.add(t, text="プレイ回数設定")
        self.p_game = self.combo(t, "対象:", ["old"] + list(pt.PROFILES), 0, "old")
        self.p_min = tk.IntVar(value=1)
        ttk.Label(t, text="最低回数:").grid(row=1, column=0, sticky="e", pady=3)
        ttk.Spinbox(t, from_=1, to=1999, textvariable=self.p_min, width=8).grid(row=1, column=1, sticky="w")
        ttk.Button(t, text="実行", command=self.do_plays).grid(row=2, column=1, sticky="w", pady=8)

        # 復元
        t = ttk.Frame(nb, padding=10); nb.add(t, text="プレイ済み復元")
        self.s_game = self.combo(t, "対象:", list(pt.PROFILES), 0, "popn7")
        self.s_keep = self.combo(t, "復元する情報:", list(KEEP_CHOICES), 1, "既定")
        self.s_src = tk.StringVar()
        ttk.Label(t, text="バックアップ:").grid(row=2, column=0, sticky="e", pady=3)
        ttk.Entry(t, textvariable=self.s_src, width=50).grid(row=2, column=1, sticky="we")
        ttk.Button(t, text="参照...", command=self.browse_src).grid(row=2, column=2, padx=5)
        ttk.Button(t, text="実行", command=self.do_restore).grid(row=3, column=1, sticky="w", pady=8)

        self.log = tk.Text(self, height=14, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    def combo(self, parent, label, values, row, default):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", pady=3)
        v = tk.StringVar(value=default)
        ttk.Combobox(parent, textvariable=v, values=values, state="readonly", width=24).grid(
            row=row, column=1, sticky="w", padx=3)
        return v

    def browse(self):
        p = filedialog.askopenfilename(title="メモリーカード", filetypes=[("PS2 メモリーカード", "*.ps2 *.mc2 *.bin"), ("すべて", "*.*")])
        if p:
            self.card.set(p)

    def browse_src(self):
        p = filedialog.askopenfilename(title="バックアップ", initialdir=os.path.join(pt.HERE, "backup"),
                                       filetypes=[("PS2 メモリーカード", "*.ps2"), ("すべて", "*.*")])
        if p:
            self.s_src.set(p)

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def run(self, fn, args, write=False):
        if not os.path.isfile(self.card.get()):
            return messagebox.showerror("エラー", "メモリーカードのファイルを選択してください")
        if write and not self.dry.get():
            if not messagebox.askyesno("確認", "カードに書き込みます (自動バックアップあり)。続行しますか?"):
                return
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn(args)
        except SystemExit as e:
            if e.code not in (None, 0):
                buf.write(f"エラー: {e.code}\n")
        except Exception as e:  # noqa: BLE001
            buf.write(f"例外: {e!r}\n")
        self.write(buf.getvalue() + "\n")

    def do_info(self):
        self.run(pt.cmd_info, Namespace(card=self.card.get()))

    def do_reset(self):
        self.run(pt.cmd_reset, Namespace(card=self.card.get(), game=self.r_game.get(),
                                         keep=KEEP_CHOICES[self.r_keep.get()], dry_run=self.dry.get()), True)

    def do_plays(self):
        self.run(pt.cmd_setplays, Namespace(card=self.card.get(), game=self.p_game.get(),
                                            min=self.p_min.get(), dry_run=self.dry.get()), True)

    def do_restore(self):
        if not os.path.isfile(self.s_src.get()):
            return messagebox.showerror("エラー", "バックアップファイルを選択してください")
        self.run(pt.cmd_restore, Namespace(card=self.card.get(), game=self.s_game.get(), src=self.s_src.get(),
                                           keep=KEEP_CHOICES[self.s_keep.get()], dry_run=self.dry.get()), True)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
