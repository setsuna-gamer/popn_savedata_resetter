"""セーブ本体を snapshots/<ラベル>/ に取り出す、または 2 つのスナップショットを比較する。
  python snap.py take <カード.ps2> <ラベル>      # 全 popn セーブを保存
  python snap.py diff <ラベルA> <ラベルB>        # バイト差分を表示
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps2mc

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")

def take(card, label):
    c = ps2mc.Card(card)
    out = os.path.join(ROOT, label); os.makedirs(out, exist_ok=True)
    for e in c.listdir():
        if e.is_dir and "popn" in e.name:
            for f in c.listdir(e):
                if f.name.startswith("BISLPM"):
                    open(os.path.join(out, f.name + ".bin"), "wb").write(c.read_file(f))
                    print("saved", f.name, f.length)

def diff(a, b):
    for fn in sorted(os.listdir(os.path.join(ROOT, a))):
        pa = os.path.join(ROOT, a, fn); pb = os.path.join(ROOT, b, fn)
        if not os.path.exists(pb): continue
        x, y = open(pa, "rb").read(), open(pb, "rb").read()
        d = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
        if not d and len(x) == len(y): continue
        print(f"== {fn}: {len(d)} bytes differ")
        runs = []
        for i in d:
            if runs and i - runs[-1][1] <= 1: runs[-1][1] = i
            else: runs.append([i, i])
        for s, e in runs[:80]:
            print(f"  0x{s:05x}-0x{e:05x}  {x[s:e+1].hex()} -> {y[s:e+1].hex()}")

if __name__ == "__main__":
    if sys.argv[1] == "take": take(sys.argv[2], sys.argv[3])
    else: diff(sys.argv[2], sys.argv[3])
