"""GUI version of popn_tool.py (tkinter) / popn_tool.py の GUI 版。  Run: python popn_gui.py"""
import contextlib
import io
import json
import os
import sys
import tkinter as tk
from argparse import Namespace
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n  # noqa: E402
import popn_tool as pt  # noqa: E402
from i18n import t  # noqa: E402

KEEP_KEYS = ["default", "plays,extra", "plays", "extra", "none"]
KEEP_VALUES = {"default": None, "plays,extra": "plays,extra", "plays": "plays", "extra": "extra", "none": "none"}
SETTINGS = os.path.join(pt.HERE, "popn_savedata_resetter.json")


def load_lang():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            lang = json.load(f).get("lang")
        if lang in i18n.LANGS:
            return lang
    except (OSError, ValueError):
        pass
    return None


def save_lang(lang):
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)
    except OSError:
        pass


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=10)
        self.root = root
        self.pack(fill="both", expand=True)
        root.geometry("780x580")

        self.card = tk.StringVar()
        self.dry = tk.BooleanVar(value=True)
        self.r_game = tk.StringVar(value="all")
        self.p_game = tk.StringVar(value="old")
        self.s_game = tk.StringVar(value="popn7")
        self.p_min = tk.IntVar(value=1)
        self.s_src = tk.StringVar()
        # keep selections are stored as language-independent keys
        self.r_keep = tk.StringVar(value="default")
        self.s_keep = tk.StringVar(value="default")
        self.lang_var = tk.StringVar(value=i18n.LANGS[i18n.get_lang()])
        self.log_text = ""
        self.build()

    def keep_combo(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", pady=3)
        labels = [t("keep." + k) for k in KEEP_KEYS]
        cb = ttk.Combobox(parent, values=labels, state="readonly", width=24)
        cb.current(KEEP_KEYS.index(var.get()))
        cb.bind("<<ComboboxSelected>>", lambda _e: var.set(KEEP_KEYS[cb.current()]))
        cb.grid(row=row, column=1, sticky="w", padx=3)

    def combo(self, parent, label, values, row, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", pady=3)
        ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=24).grid(
            row=row, column=1, sticky="w", padx=3)

    def build(self):
        if hasattr(self, "log"):
            self.log_text = self.log.get("1.0", "end-1c")
        for w in self.winfo_children():
            w.destroy()
        self.root.title(t("app_title"))

        row = ttk.Frame(self); row.pack(fill="x", pady=(0, 6))
        ttk.Label(row, text=t("language")).pack(side="left")
        lc = ttk.Combobox(row, textvariable=self.lang_var, values=list(i18n.LANGS.values()),
                          state="readonly", width=10)
        lc.pack(side="left", padx=5)
        lc.bind("<<ComboboxSelected>>", self.change_lang)

        row = ttk.Frame(self); row.pack(fill="x")
        ttk.Label(row, text=t("card")).pack(side="left")
        ttk.Entry(row, textvariable=self.card).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(row, text=t("browse"), command=self.browse).pack(side="left")
        ttk.Button(row, text=t("show_info"), command=self.do_info).pack(side="left", padx=(5, 0))

        ttk.Checkbutton(self, text=t("dry_run_check"), variable=self.dry).pack(anchor="w", pady=5)

        nb = ttk.Notebook(self); nb.pack(fill="x")
        games = ["all"] + list(pt.PROFILES)

        tab = ttk.Frame(nb, padding=10); nb.add(tab, text=t("tab_reset"))
        self.combo(tab, t("target"), games, 0, self.r_game)
        self.keep_combo(tab, t("keep_label"), self.r_keep, 1)
        ttk.Button(tab, text=t("run"), command=self.do_reset).grid(row=2, column=1, sticky="w", pady=8)

        tab = ttk.Frame(nb, padding=10); nb.add(tab, text=t("tab_plays"))
        self.combo(tab, t("target"), ["old"] + list(pt.PROFILES), 0, self.p_game)
        ttk.Label(tab, text=t("min_plays")).grid(row=1, column=0, sticky="e", pady=3)
        ttk.Spinbox(tab, from_=1, to=1999, textvariable=self.p_min, width=8).grid(row=1, column=1, sticky="w")
        ttk.Button(tab, text=t("run"), command=self.do_plays).grid(row=2, column=1, sticky="w", pady=8)

        tab = ttk.Frame(nb, padding=10); nb.add(tab, text=t("tab_restore"))
        self.combo(tab, t("target"), list(pt.PROFILES), 0, self.s_game)
        self.keep_combo(tab, t("restore_label"), self.s_keep, 1)
        ttk.Label(tab, text=t("backup_file")).grid(row=2, column=0, sticky="e", pady=3)
        ttk.Entry(tab, textvariable=self.s_src, width=50).grid(row=2, column=1, sticky="we")
        ttk.Button(tab, text=t("browse"), command=self.browse_src).grid(row=2, column=2, padx=5)
        ttk.Button(tab, text=t("run"), command=self.do_restore).grid(row=3, column=1, sticky="w", pady=8)

        self.log = tk.Text(self, height=14, state="normal", wrap="word")
        self.log.insert("end", self.log_text)
        self.log.configure(state="disabled")
        self.log.pack(fill="both", expand=True, pady=(8, 0))

    def change_lang(self, _event=None):
        lang = next((k for k, v in i18n.LANGS.items() if v == self.lang_var.get()), "ja")
        i18n.set_lang(lang)
        save_lang(lang)
        self.build()

    def filetypes(self, *exts):
        return [(t("ft_card"), " ".join(exts)), (t("ft_all"), "*.*")]

    def browse(self):
        p = filedialog.askopenfilename(title=t("dlg_card"), filetypes=self.filetypes("*.ps2", "*.mc2", "*.bin"))
        if p:
            self.card.set(p)

    def browse_src(self):
        p = filedialog.askopenfilename(title=t("dlg_backup"), initialdir=os.path.join(pt.HERE, "backup"),
                                       filetypes=self.filetypes("*.ps2"))
        if p:
            self.s_src.set(p)

    def write(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def run(self, fn, args, write=False):
        if not os.path.isfile(self.card.get()):
            return messagebox.showerror(t("error"), t("select_card"))
        if write and not self.dry.get():
            if not messagebox.askyesno(t("confirm"), t("confirm_write")):
                return
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn(args)
        except SystemExit as e:
            if e.code not in (None, 0):
                buf.write(t("gui_error", e=e.code) + "\n")
        except Exception as e:  # noqa: BLE001
            buf.write(t("gui_exception", e=repr(e)) + "\n")
        self.write(buf.getvalue() + "\n")

    def do_info(self):
        self.run(pt.cmd_info, Namespace(card=self.card.get()))

    def do_reset(self):
        self.run(pt.cmd_reset, Namespace(card=self.card.get(), game=self.r_game.get(),
                                         keep=KEEP_VALUES[self.r_keep.get()], dry_run=self.dry.get()), True)

    def do_plays(self):
        self.run(pt.cmd_setplays, Namespace(card=self.card.get(), game=self.p_game.get(),
                                            min=self.p_min.get(), dry_run=self.dry.get()), True)

    def do_restore(self):
        if not os.path.isfile(self.s_src.get()):
            return messagebox.showerror(t("error"), t("select_backup"))
        self.run(pt.cmd_restore, Namespace(card=self.card.get(), game=self.s_game.get(), src=self.s_src.get(),
                                           keep=KEEP_VALUES[self.s_keep.get()], dry_run=self.dry.get()), True)


if __name__ == "__main__":
    saved = load_lang()
    if saved:
        i18n.set_lang(saved)
    root = tk.Tk()
    App(root)
    root.mainloop()
