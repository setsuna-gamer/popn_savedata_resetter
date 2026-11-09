"""Minimal i18n (Japanese / English) shared by the CLI, the GUI and ps2mc.

    import i18n
    i18n.set_lang("en")
    i18n.t("done")
"""
import locale
import os

LANGS = {"ja": "日本語", "en": "English"}

MESSAGES = {
    # ---- common / CLI ----
    "unsupported_game": {
        "ja": "{game} は未対応です。対応: {supported}",
        "en": "{game} is not supported. Supported: {supported}"},
    "save_not_found": {
        "ja": "{title} のセーブがカード内に見つかりません",
        "en": "Save data for {title} was not found on the card"},
    "checksum_corrupt": {
        "ja": "{title}: チェックサムを検出できません (セーブが破損している可能性)。中止します",
        "en": "{title}: could not locate the checksum (the save may be corrupted). Aborting"},
    "checksum_fail": {
        "ja": "チェックサムを検出できません。中止します",
        "en": "Could not locate the checksum. Aborting"},
    "keep_invalid": {
        "ja": "--keep に使えるのは plays / extra / none です: {bad}",
        "en": "--keep accepts only plays / extra / none: {bad}"},
    "not_slot_format": {
        "ja": "このバージョンはスロット形式ではないため未対応です",
        "en": "This version does not use the slot format and is not supported"},
    "reset_msg": {
        "ja": "{title}: レコードをリセットします ({changed} バイト変更)",
        "en": "{title}: resetting records ({changed} bytes changed)"},
    "dry_run_skip": {
        "ja": "--dry-run のため書き込みません",
        "en": "Dry run: nothing was written"},
    "pcsx2_running": {
        "ja": "PCSX2 が起動中です。終了してから再実行してください",
        "en": "PCSX2 is running. Close it and run again"},
    "backup": {"ja": "バックアップ:", "en": "Backup:"},
    "done": {"ja": "完了", "en": "Done"},
    "restore_no_fields": {
        "ja": "復元するフィールドがありません (--keep plays,extra を指定してください)",
        "en": "No fields to restore (specify --keep plays,extra)"},
    "restore_save_missing": {
        "ja": "カードまたはバックアップにセーブが見つかりません",
        "en": "Save data was not found on the card or in the backup"},
    "restore_msg": {
        "ja": "{title}: プレイ済み情報({keep})を復元します ({changed} バイト変更)",
        "en": "{title}: restoring played data ({keep}) ({changed} bytes changed)"},
    "min_range": {
        "ja": "--min は 1〜1999 で指定してください",
        "en": "--min must be between 1 and 1999"},
    "setplays_msg": {
        "ja": "{title}: {n} 譜面のプレイ回数を {min} にします",
        "en": "{title}: setting play count to {min} for {n} charts"},
    "info_supported": {"ja": "対応", "en": "supported"},
    "info_unsupported": {"ja": "未対応", "en": "unsupported"},
    # ---- ps2mc ----
    "mc_not_card_image": {
        "ja": "メモリーカードイメージとして認識できません",
        "en": "Not recognized as a memory card image"},
    "mc_not_ps2": {
        "ja": "PS2 メモリーカードではありません",
        "en": "Not a PS2 memory card"},
    "mc_size_change": {
        "ja": "ファイルサイズが変わる書き込みは未対応です",
        "en": "Writes that change the file size are not supported"},
    # ---- GUI ----
    "app_title": {"ja": "pop'n music セーブデータツール", "en": "pop'n music Save Data Tool"},
    "language": {"ja": "言語:", "en": "Language:"},
    "card": {"ja": "メモリーカード:", "en": "Memory card:"},
    "browse": {"ja": "参照...", "en": "Browse..."},
    "show_info": {"ja": "情報表示", "en": "Show info"},
    "dry_run_check": {"ja": "ドライラン (書き込まず確認のみ)", "en": "Dry run (preview only, do not write)"},
    "tab_reset": {"ja": "レコードリセット", "en": "Reset records"},
    "tab_plays": {"ja": "プレイ回数設定", "en": "Set play count"},
    "tab_restore": {"ja": "プレイ済み復元", "en": "Restore played"},
    "target": {"ja": "対象:", "en": "Target:"},
    "keep_label": {"ja": "残す情報:", "en": "Keep:"},
    "restore_label": {"ja": "復元する情報:", "en": "Restore:"},
    "min_plays": {"ja": "最低回数:", "en": "Minimum:"},
    "backup_file": {"ja": "バックアップ:", "en": "Backup file:"},
    "run": {"ja": "実行", "en": "Run"},
    "keep.default": {"ja": "既定", "en": "Default"},
    "keep.plays,extra": {"ja": "プレイ回数+クリア印", "en": "Play count + clear marks"},
    "keep.plays": {"ja": "プレイ回数のみ", "en": "Play count only"},
    "keep.extra": {"ja": "クリア印のみ", "en": "Clear marks only"},
    "keep.none": {"ja": "なし (全消去)", "en": "None (erase all)"},
    "ft_card": {"ja": "PS2 メモリーカード", "en": "PS2 memory card"},
    "ft_all": {"ja": "すべて", "en": "All files"},
    "dlg_card": {"ja": "メモリーカード", "en": "Memory card"},
    "dlg_backup": {"ja": "バックアップ", "en": "Backup"},
    "error": {"ja": "エラー", "en": "Error"},
    "select_card": {"ja": "メモリーカードのファイルを選択してください", "en": "Please select a memory card file"},
    "select_backup": {"ja": "バックアップファイルを選択してください", "en": "Please select a backup file"},
    "confirm": {"ja": "確認", "en": "Confirm"},
    "confirm_write": {
        "ja": "カードに書き込みます (自動バックアップあり)。続行しますか?",
        "en": "This will write to the card (an automatic backup is made). Continue?"},
    "gui_error": {"ja": "エラー: {e}", "en": "Error: {e}"},
    "gui_exception": {"ja": "例外: {e}", "en": "Exception: {e}"},
}

_lang = "ja"


def detect_lang():
    env = os.environ.get("POPN_LANG", "").lower()
    if env[:2] in LANGS:
        return env[:2]
    try:
        loc = (locale.getlocale()[0] or os.environ.get("LANG", "") or "").lower()
    except Exception:  # noqa: BLE001
        loc = ""
    return "ja" if loc.startswith("ja") or "japan" in loc else "en"


def set_lang(lang):
    global _lang
    if lang in LANGS:
        _lang = lang


def get_lang():
    return _lang


def t(key, **kw):
    text = MESSAGES[key][_lang]
    return text.format(**kw) if kw else text


set_lang(detect_lang())
