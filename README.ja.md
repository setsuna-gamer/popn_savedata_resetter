# popn_savedata_resetter

[English](README.md) | **日本語**

PS2 版 pop'n music のセーブデータ（PCSX2 のメモリーカードイメージ `.ps2` / `.bin`）を改変するツールです。
GUI 版 (tkinter) と CLI 版があります。

## 対応タイトル

pop'n music 7 / 8 / 9 / 10 / 11 / 12 いろは / BEST HITS!

## 機能

| コマンド | 内容 |
|---|---|
| `info` | カード内のセーブデータ情報を表示 |
| `reset-records` | ランキング・レコードをリセット（プレイ回数・クリア印を残す指定も可） |
| `set-plays` | 全曲・全譜面のプレイ回数を最低 N 回にする（フリーモードで選曲できるようにする用途） |
| `restore-played` | リセット済みカードへ、バックアップからプレイ済み情報だけを書き戻す |

## 使い方

実行ファイルは [Releases](https://github.com/setsuna-gamer/popn_savedata_resetter/releases) から入手できます（Windows / macOS / Linux）。
または Python 3 で直接実行できます。

```bash
python popn_gui.py                                   # GUI
python popn_tool.py info card.ps2
python popn_tool.py --lang en info card.ps2             # 表示言語を指定 (ja / en)
python popn_tool.py reset-records card.ps2 --game popn12 --dry-run
python popn_tool.py reset-records card.ps2 --game all --keep plays,extra
python popn_tool.py set-plays card.ps2 --game old --min 1
python popn_tool.py restore-played card.ps2 --from backup.ps2 --game popn7
```

- `--game`: `popn7` `popn8` `popn9` `popn10` `popn11` `popn12` `besthits` `all`（`set-plays` は `old` = popn7/8/9/besthits も可）
- `--keep`: `plays,extra` / `plays` / `extra` / `none`（残す情報。省略時は各バージョンの既定）
- `--dry-run`: 書き込まず確認のみ
- `--lang`: 表示言語 `ja` / `en`（サブコマンドの前に指定。省略時は OS のロケールまたは環境変数 `POPN_LANG`）

GUI は画面上部の「言語」から日本語 / English を切り替えられます（選択は記憶されます）。

## 安全のために

- 書き込み前に `backup/` へタイムスタンプ付きでカードを自動バックアップします。
- PCSX2 起動中は書き込みを拒否します（カード破損防止）。必ず終了してから実行してください。
- ファイルの同サイズ上書きのみ行い、FAT／ディレクトリ構造は変更しません。書き込んだページの ECC は再計算します。
- 重要なデータは、本ツールの自動バックアップとは別にも必ず取っておいてください。

## ビルド

```bash
pip install pyinstaller
python build.py
```

`dist/` に `popn_savedata_resetter_gui` と `popn_savedata_resetter_cli` が出力されます。
クロスコンパイルはできないため各 OS 上で実行してください。`v*` タグを push すると GitHub Actions が 3 OS 向けにビルドし、Releases に公開します。

## 免責事項・注意事項

- **自己責任でご利用ください。** 本ツールの使用によって生じたいかなる損害（セーブデータの破損・消失など）についても、作者は責任を負いません。
- 本ツールは**非公式**のものであり、株式会社コナミアミューズメント／コナミグループ、およびソニー・インタラクティブエンタテインメントとは一切関係ありません。**これらの企業へ本ツールについて問い合わせないでください。**
- 「pop'n music」「PlayStation 2」などの名称は各社の商標または登録商標です。
- 本リポジトリにはゲームのデータ（ROM・ディスクイメージ・セーブデータ）は含まれていません。ご自身が正当に所有するデータに対してのみ使用してください。
- 予告なく**公開を終了する場合があります**（リポジトリの削除・非公開化、Releases の取り下げなど）。
- 不具合報告は GitHub の Issues で受け付けますが、対応は保証しません。

## ライセンス

[MIT License](LICENSE)
