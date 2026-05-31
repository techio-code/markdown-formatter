"""
L2 Playwright test — markdown-formatter/index.html
動作確認: テキスト入力 → Markdown変換 → プレビュー切替 → コピー/DL機能
"""
import re
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

HTML_PATH = Path(__file__).parent / "index.html"
URL = HTML_PATH.as_uri()


def test_page_loads():
    """ページが正常に読み込まれる"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        # タイトル確認
        assert "Markdown" in page.title()

        # 2パネル構成が存在する
        assert page.locator(".panel-left").count() == 1
        assert page.locator(".panel").count() == 2

        # ヘッダー要素
        assert page.locator(".header-title").inner_text() == "Markdown 整形ツール"
        assert page.locator(".header-accent").count() == 1  # coffeeアクセント縦線

        browser.close()


def test_format_converts_bullet_and_heading():
    """テキスト → 見出し・箇条書きが正しく変換される"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        textarea = page.locator("#inputArea")
        textarea.fill("1. はじめに\n・概要説明\n・背景と目的\n2. 本題\n内容をここに書く")

        page.locator("#btnFormat").click()

        raw_text = page.locator("#outputRaw").inner_text()
        assert "## はじめに" in raw_text, f"見出し変換失敗: {raw_text}"
        assert "- 概要説明" in raw_text, f"箇条書き変換失敗: {raw_text}"
        assert "- 背景と目的" in raw_text
        assert "## 本題" in raw_text

        browser.close()


def test_live_preview_autofires():
    """デバウンス後に自動整形が走る（タイプで自動整形）"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        textarea = page.locator("#inputArea")
        textarea.type("・自動テスト\n1. 項目A")

        # デバウンス待機（500ms + マージン）
        page.wait_for_timeout(800)

        raw_text = page.locator("#outputRaw").inner_text()
        assert "- 自動テスト" in raw_text, f"自動整形失敗: {raw_text}"

        browser.close()


def test_preview_tab_renders_html():
    """プレビュータブに切り替えるとHTMLレンダリングされる"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        # サンプルボタンで入力
        page.locator("#btnExample").click()
        page.wait_for_timeout(800)

        # プレビュータブに切り替え
        page.locator(".tab-btn[data-view='preview']").click()
        page.wait_for_timeout(200)

        preview = page.locator("#outputPreview")
        assert preview.is_visible()

        # h2 タグが生成されている
        h2_count = preview.locator("h2").count()
        assert h2_count > 0, "プレビューにh2が生成されていない"

        # li タグも生成されている
        li_count = preview.locator("li").count()
        assert li_count > 0, f"プレビューにliが生成されていない (h2={h2_count})"

        browser.close()


def test_stats_update_after_format():
    """整形後にステータスバーのstatsが更新される"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        page.locator("#btnExample").click()
        page.wait_for_timeout(800)

        lines_text = page.locator("#statLines").inner_text()
        chars_text = page.locator("#statChars").inner_text()

        assert "行" in lines_text, f"行数が表示されない: {lines_text}"
        assert "字" in chars_text, f"文字数が表示されない: {chars_text}"

        # 数値が入っている
        lines_num = int(re.search(r"\d+", lines_text).group())
        assert lines_num > 0

        browser.close()


def test_clear_button():
    """クリアボタンで入力・出力がリセットされる"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        page.locator("#btnExample").click()
        page.wait_for_timeout(800)

        page.locator("#btnClear").click()

        assert page.locator("#inputArea").input_value() == ""
        raw_text = page.locator("#outputRaw").inner_text()
        assert "整形結果がここに表示されます" in raw_text

        browser.close()


def test_insert_toolbar_h2():
    """挿入ツールバーのH2ボタンがtextareaに挿入される"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        page.locator("#inputArea").click()
        page.locator(".ins-btn[data-insert='## ']").click()

        val = page.locator("#inputArea").input_value()
        assert "## " in val, f"H2挿入失敗: {val}"

        browser.close()


def test_options_checkboxes_affect_output():
    """「見出し自動検出」チェックを外すと変換されない"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        # 見出し自動検出をOFF
        page.locator("#chkHeading").uncheck()
        page.locator("#inputArea").fill("1. はじめに")
        page.locator("#btnFormat").click()

        raw_text = page.locator("#outputRaw").inner_text()
        # ##変換されていないこと
        assert "## はじめに" not in raw_text, f"チェックOFF時に変換された: {raw_text}"

        browser.close()


def test_download_button_exists():
    """ダウンロードボタンが存在し、整形後にクリックできる"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)

        page.locator("#btnExample").click()
        page.wait_for_timeout(800)

        dl_btn = page.locator("#btnDownload")
        assert dl_btn.is_visible()
        assert dl_btn.is_enabled()

        browser.close()


def test_mobile_layout():
    """モバイルビューポートでページが壊れない"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(URL)

        # 基本要素が表示されている
        assert page.locator("#inputArea").is_visible()
        assert page.locator("#outputRaw").is_visible()
        assert page.locator(".btn-format-sm").is_visible()

        browser.close()


if __name__ == "__main__":
    import sys
    tests = [
        test_page_loads,
        test_format_converts_bullet_and_heading,
        test_live_preview_autofires,
        test_preview_tab_renders_html,
        test_stats_update_after_format,
        test_clear_button,
        test_insert_toolbar_h2,
        test_options_checkboxes_affect_output,
        test_download_button_exists,
        test_mobile_layout,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed / {failed} failed")
    sys.exit(0 if failed == 0 else 1)
