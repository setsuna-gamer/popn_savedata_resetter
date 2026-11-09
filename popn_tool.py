"""PS2 pop'n music セーブデータ改変ツール (メモリーカードイメージ用)

使い方:
  python popn_tool.py info  <カード.ps2>
  python popn_tool.py reset-records <カード.ps2> --game popn12 [--dry-run]
  python popn_tool.py reset-records <カード.ps2> --game all    [--dry-run]   (対応済みを全部)
      --keep plays,extra | plays | extra | none   プレイ済み情報を残す指定 (省略時は各バージョンの既定)
  python popn_tool.py set-plays <カード.ps2> [--game old|popn7|...] [--min 1] [--dry-run]
      全曲・全譜面のプレイ回数を最低 --min 回にする (フリーモードで選曲できるようにする用途)
      old = popn7 / besthits / popn8 / popn9 (省略時)
  python popn_tool.py restore-played <カード.ps2> --from <バックアップ.ps2> --game popn7 [--keep ...]
      リセット済みのカードに、バックアップからプレイ済み情報だけを書き戻す

書き込み前に backup/ へタイムスタンプ付きでカードを自動バックアップする。
PCSX2 が起動中の場合は書き込まない (カードが壊れるため)。
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ps2mc  # noqa: E402

if getattr(sys, "frozen", False):  # PyInstaller でビルドされた実行ファイル
    HERE = os.path.dirname(os.path.abspath(sys.executable))
    if ".app" + os.sep + "Contents" in HERE:  # macOS の .app バンドルの外側に置く
        HERE = HERE.split(".app" + os.sep + "Contents")[0].rsplit(os.sep, 1)[0]
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

# ---- バージョンごとの定義 (解析済みのもののみ) ----
# ranking : 12 バイト (score u32 + name 8byte) のエントリが 5 件 x groups 組並ぶ表
# records : 12 バイト (score u32 + 状態 u32 + 予備 u32) のスロット領域 [start, end)
# records の mode:
#   "zero"  : 領域全体をゼロで埋める (popn12)
#   "slots" : 12 バイトスロット (score u32, プレイ回数 u16, コンボ u16, u32) のうち
#             記録済みのものだけを初期値 (score=default_score, コンボ 0) に戻す。
#             "keep" に指定したフィールドは消さずに残す:
#               plays = プレイ回数 (u16) / extra = 末尾の u32 (クリア印と思われる)
#             解放状況がプレイ済み判定に依存するバージョンのため。
PROFILES = {
    "popn7": dict(title="pop'n music 7", dir="BISLPM-65208popn7",
                  ranking=dict(start=0xA8, groups=56, per=5),
                  records=dict(mode="slots", start=0xDC8, end=0x20C4, default_score=10000,
                               keep=("plays", "extra"))),
    "besthits": dict(title="pop'n music BEST HITS!", dir="BISLPM-62288popnb",
                     ranking=dict(start=0x60, groups=10, per=5),
                     records=dict(mode="slots", start=0x2B8, end=0xCD8, default_score=10000,
                                   keep=("plays", "extra"))),
    "popn8": dict(title="pop'n music 8", dir="BISLPM-65316popn8",
                  ranking=dict(start=0xAC, groups=76, per=5),
                  records=dict(mode="slots", start=0x127C, end=0x271C, default_score=10000,
                               keep=("plays", "extra"))),
    "popn9": dict(title="pop'n music 9", dir="BISLPM-65508popn9",
                  ranking=dict(start=0x17C, groups=73, per=5),
                  records=dict(mode="slots", start=0x1298, end=0x2768, default_score=0,
                               keep=("plays", "extra"))),
    "popn10": dict(title="pop'n music 10", dir="BISLPM-65770popn10",
                   ranking=dict(start=0x11C, groups=84, per=5),
                   records=dict(mode="slots", start=0x14CC, end=0x28AC, default_score=0)),
    "popn11": dict(title="pop'n music 11", dir="BISLPM-66065popn11",
                   ranking=dict(start=0x144, groups=60, per=5),
                   records=dict(mode="slots", start=0xF54, end=0x3B34, default_score=0)),
    "popn12": dict(
        title="pop'n music 12 いろは",
        dir="BISLPM-66314popn12",
        ranking=dict(start=0x120, groups=64, per=5),
        records=dict(mode="zero", start=0x1020, end=0x2C40),
    ),
}
ALL_DIRS = {
    "besthits": "BISLPM-62288popnb",
    "popn7": "BISLPM-65208popn7", "popn8": "BISLPM-65316popn8",
    "popn9": "BISLPM-65508popn9", "popn10": "BISLPM-65770popn10",
    "popn11": "BISLPM-66065popn11", "popn12": "BISLPM-66314popn12",
    "popn13": "BISLPM-66533popn13", "popn14": "BISLPM-66742popn14",
}
DEFAULT_RANK = [100000, 90000, 80000, 70000, 60000]


# ---- チェックサム (先頭〜直前の総和 mod 256 を 1 バイトで保持) ----
def find_checksum_pos(buf):
    hits = [p for p in range(len(buf) - 16, len(buf)) if sum(buf[:p]) & 255 == buf[p]]
    return hits[0] if len(hits) == 1 else None


def fix_checksum(buf, pos):
    buf[pos] = sum(buf[:pos]) & 255


# ---- 操作 ----
def parse_keep(text, prof):
    """--keep の指定を ('plays','extra') の部分集合にする。None なら既定値"""
    if text is None:
        return tuple(prof["records"].get("keep", ()))
    if text.strip().lower() in ("none", ""):
        return ()
    keep = tuple(x.strip() for x in text.split(","))
    bad = [x for x in keep if x not in ("plays", "extra")]
    if bad:
        sys.exit(f"--keep に使えるのは plays / extra / none です: {bad}")
    return keep


def reset_records(buf, prof, keep=()):
    r = prof["ranking"]
    for g in range(r["groups"]):
        for i in range(r["per"]):
            o = r["start"] + 12 * (r["per"] * g + i)
            struct.pack_into("<I", buf, o, DEFAULT_RANK[i])
            buf[o + 4:o + 12] = b"POPN\0\0\0\0"
    rec = prof["records"]
    if rec["mode"] == "zero":
        buf[rec["start"]:rec["end"]] = bytes(rec["end"] - rec["start"])
        return
    for o in range(rec["start"], rec["end"], 12):
        score, plays, combo, extra = struct.unpack_from("<IHHI", buf, o)
        # 記録済みスロットの形のものだけ初期化 (想定外の値は触らない)
        if not (score <= 100000 and plays < 2000 and combo < 2000 and extra < 16):
            continue
        if rec["default_score"] and score == 0:
            continue  # 初期値が 10000 の版でスコア 0 のスロットは曲データ外の余白
        new = (rec["default_score"], plays if "plays" in keep else 0, 0,
               extra if "extra" in keep else 0)
        if new != (score, plays, combo, extra):
            struct.pack_into("<IHHI", buf, o, *new)


def set_min_plays(buf, prof, minimum):
    """スロット領域の全譜面のプレイ回数を最低 minimum にする (増やすだけで減らさない)"""
    rec = prof["records"]
    if rec["mode"] != "slots":
        sys.exit("このバージョンはスロット形式ではないため未対応です")
    n = 0
    for o in range(rec["start"], rec["end"], 12):
        score, plays, combo, extra = struct.unpack_from("<IHHI", buf, o)
        # 想定外の形のスロットは触らない。初期値が 10000 のバージョンでは、
        # スコア 0 のスロットは曲データの外 (余白) なので触らない
        if not (score <= 100000 and plays < 2000 and combo < 2000 and extra < 16):
            continue
        if rec["default_score"] and score == 0:
            continue
        if plays < minimum:
            struct.pack_into("<H", buf, o + 4, minimum)
            n += 1
    return n


def restore_played(buf, old, prof, keep):
    """リセット済み buf に、old (リセット前) のプレイ済み情報だけを書き戻す"""
    rec = prof["records"]
    if rec["mode"] != "slots":
        sys.exit("このバージョンはスロット形式ではないため未対応です")
    for o in range(rec["start"], rec["end"], 12):
        s0, p0, c0, x0 = struct.unpack_from("<IHHI", old, o)
        score, plays, combo, extra = struct.unpack_from("<IHHI", buf, o)
        if not (s0 <= 100000 and p0 < 2000 and c0 < 2000 and x0 < 16):
            continue
        # 旧バージョンのバグで余白 (元はオール0) が初期値に書き換わっていたものを元に戻す
        if rec["default_score"] and (s0, p0, c0, x0) == (0, 0, 0, 0)                 and (score, plays, combo, extra) == (rec["default_score"], 0, 0, 0):
            struct.pack_into("<IHHI", buf, o, 0, 0, 0, 0)
            continue
        # まだリセット直後の状態 (スコア初期値・コンボ0) のスロットだけ復元する
        if score != rec["default_score"] or combo != 0:
            continue
        struct.pack_into("<IHHI", buf, o, score,
                         p0 if "plays" in keep else plays, combo,
                         x0 if "extra" in keep else extra)


def pcsx2_running():
    try:
        cmd = ["tasklist"] if os.name == "nt" else ["ps", "-A", "-o", "comm="]
        out = subprocess.run(cmd, capture_output=True).stdout.lower()
    except OSError:
        return False
    return b"pcsx2" in out


def backup(path):
    os.makedirs(os.path.join(HERE, "backup"), exist_ok=True)
    dst = os.path.join(HERE, "backup", time.strftime("%Y%m%d-%H%M%S_") + os.path.basename(path))
    shutil.copy2(path, dst)
    return dst


def find_save(card, dirname):
    d = card.find_dir(dirname)
    if d is None:
        return None
    for f in card.listdir(d):
        if f.name == dirname and f.is_file:
            return f
    return None


def cmd_info(args):
    card = ps2mc.Card(args.card)
    for key, dn in ALL_DIRS.items():
        f = find_save(card, dn)
        if f is None:
            continue
        buf = bytearray(card.read_file(f))
        pos = find_checksum_pos(buf)
        sup = "対応" if key in PROFILES else "未対応"
        print(f"{key:7s} {dn:22s} {len(buf):6d}B  checksum@{hex(pos) if pos else '?':7s} [{sup}]")


def cmd_reset(args):
    keys = list(PROFILES) if args.game == "all" else [args.game]
    for k in keys:
        if k not in PROFILES:
            sys.exit(f"{k} は未対応です。対応: {', '.join(PROFILES)}")
    card = ps2mc.Card(args.card)
    jobs = []
    for k in keys:
        prof = PROFILES[k]
        f = find_save(card, prof["dir"])
        if f is None:
            if args.game == "all":
                continue
            sys.exit(f"{prof['title']} のセーブがカード内に見つかりません")
        buf = bytearray(card.read_file(f))
        pos = find_checksum_pos(buf)
        if pos is None:
            sys.exit(f"{prof['title']}: チェックサムを検出できません (セーブが破損している可能性)。中止します")
        before = bytes(buf)
        reset_records(buf, prof, parse_keep(args.keep, prof))
        fix_checksum(buf, pos)
        changed = sum(1 for a, b in zip(before, buf) if a != b)
        print(f"{prof['title']}: レコードをリセットします ({changed} バイト変更)")
        jobs.append((f, bytes(buf)))
    if args.dry_run:
        print("--dry-run のため書き込みません")
        return
    if not jobs:
        return
    if pcsx2_running():
        sys.exit("PCSX2 が起動中です。終了してから再実行してください")
    print("バックアップ:", backup(args.card))
    for f, data in jobs:
        card.write_file(f, data)
    card.save()
    print("完了")


def cmd_restore(args):
    prof = PROFILES.get(args.game)
    if prof is None:
        sys.exit(f"{args.game} は未対応です。対応: {', '.join(PROFILES)}")
    keep = parse_keep(args.keep, prof)
    if not keep:
        sys.exit("復元するフィールドがありません (--keep plays,extra を指定してください)")
    card = ps2mc.Card(args.card)
    src = ps2mc.Card(args.src)
    f, g = find_save(card, prof["dir"]), find_save(src, prof["dir"])
    if f is None or g is None:
        sys.exit("カードまたはバックアップにセーブが見つかりません")
    buf = bytearray(card.read_file(f))
    pos = find_checksum_pos(buf)
    if pos is None:
        sys.exit("チェックサムを検出できません。中止します")
    before = bytes(buf)
    restore_played(buf, src.read_file(g), prof, keep)
    fix_checksum(buf, pos)
    changed = sum(1 for a, b in zip(before, buf) if a != b)
    print(f"{prof['title']}: プレイ済み情報({', '.join(keep)})を復元します ({changed} バイト変更)")
    if args.dry_run:
        print("--dry-run のため書き込みません")
        return
    if pcsx2_running():
        sys.exit("PCSX2 が起動中です。終了してから再実行してください")
    print("バックアップ:", backup(args.card))
    card.write_file(f, bytes(buf))
    card.save()
    print("完了")


OLD_GAMES = ["popn7", "besthits", "popn8", "popn9"]


def cmd_setplays(args):
    keys = OLD_GAMES if args.game == "old" else [args.game]
    for k in keys:
        if k not in PROFILES:
            sys.exit(f"{k} は未対応です。対応: {', '.join(PROFILES)}")
    if not 1 <= args.min <= 1999:
        sys.exit("--min は 1〜1999 で指定してください")
    card = ps2mc.Card(args.card)
    jobs = []
    for k in keys:
        prof = PROFILES[k]
        f = find_save(card, prof["dir"])
        if f is None:
            if args.game == "old":
                continue
            sys.exit(f"{prof['title']} のセーブがカード内に見つかりません")
        buf = bytearray(card.read_file(f))
        pos = find_checksum_pos(buf)
        if pos is None:
            sys.exit(f"{prof['title']}: チェックサムを検出できません。中止します")
        n = set_min_plays(buf, prof, args.min)
        fix_checksum(buf, pos)
        print(f"{prof['title']}: {n} 譜面のプレイ回数を {args.min} にします")
        jobs.append((f, bytes(buf)))
    if args.dry_run or not jobs:
        print("--dry-run のため書き込みません" if args.dry_run else "")
        return
    if pcsx2_running():
        sys.exit("PCSX2 が起動中です。終了してから再実行してください")
    print("バックアップ:", backup(args.card))
    for f, data in jobs:
        card.write_file(f, data)
    card.save()
    print("完了")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info"); p.add_argument("card"); p.set_defaults(fn=cmd_info)
    p = sub.add_parser("reset-records"); p.add_argument("card")
    p.add_argument("--game", default="popn12"); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--keep", default=None)
    p.set_defaults(fn=cmd_reset)
    p = sub.add_parser("set-plays"); p.add_argument("card")
    p.add_argument("--game", default="old"); p.add_argument("--min", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_setplays)
    p = sub.add_parser("restore-played"); p.add_argument("card")
    p.add_argument("--from", dest="src", required=True)
    p.add_argument("--game", required=True); p.add_argument("--keep", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_restore)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
