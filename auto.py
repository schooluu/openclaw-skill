# -*- coding: utf-8 -*-
"""
交互式登录 + 侧栏菜单：
  1) 输入网址、账号、密码；canvas 验证码可 ddddocr 或手输
  2) 登录成功后，可输入画面名称（侧栏一项，适配 xr-menu / xr-sub-menu）

准备环境:
  pip install -r requirements-auto.txt
  playwright install chromium

侧栏 DOM 参考: div.xr-menu[role="menu"] 内 li.xr-sub-menu / div.xr-sub-menu-content__title span
"""

from __future__ import annotations

import getpass
import sys
import time


def _ensure_utf8_stdio() -> None:
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _ocr_captcha_from_canvas(page) -> str | None:
    """对页面上「足够大」的可见 canvas 截图并 OCR；无 ddddocr 或失败则返回 None。"""
    try:
        import ddddocr
    except ImportError:
        print("未安装 ddddocr，将跳过自动识别。可执行: pip install ddddocr")
        return None

    ocr = ddddocr.DdddOcr(show_ad=False)
    canvases = page.locator("canvas")
    n = canvases.count()
    best_png: bytes | None = None
    best_area = 0.0

    for i in range(n):
        c = canvases.nth(i)
        if not c.is_visible():
            continue
        box = c.bounding_box()
        if not box:
            continue
        area = box["width"] * box["height"]
        if area < 1500:
            continue
        png = c.screenshot()
        if area > best_area:
            best_area = area
            best_png = png

    if best_png is None:
        for i in range(n):
            c = canvases.nth(i)
            if c.is_visible():
                best_png = c.screenshot()
                break

    if not best_png:
        return None

    try:
        text = ocr.classification(best_png)
        return (text or "").strip()
    except Exception as exc:  # noqa: BLE001
        print("OCR 异常:", exc)
        return None


def _click_sidebar_label(page, label: str) -> None:
    """在左侧 xr-menu 中点击与 label 完全匹配的一项（先匹配一级标题 span，否则在滚动区内按精确文案点）。"""
    label = label.strip()
    if not label:
        return

    menu = page.locator('div.xr-menu[role="menu"]').first
    menu.wait_for(state="visible", timeout=60_000)

    titles = menu.locator("div.xr-sub-menu-content__title span")
    for i in range(titles.count()):
        span = titles.nth(i)
        try:
            if span.inner_text().strip() == label:
                row = span.locator(
                    "xpath=ancestor::div[contains(@class,'xr-sub-menu-content')][1]",
                )
                row.scroll_into_view_if_needed()
                row.click(timeout=15_000)
                time.sleep(0.35)
                return
        except Exception:
            continue

    # 子级/叶子可能不在 xr-sub-menu-content__title 同一结构：在侧栏滚动容器内按精确文本点第一个可见项
    bar = page.locator(".xl-scrollbar.xr-menu-scrollbar").first
    target = bar.get_by_text(label, exact=True).first
    target.scroll_into_view_if_needed()
    target.click(timeout=15_000)
    time.sleep(0.35)


def main() -> None:
    _ensure_utf8_stdio()

    url = input("访问网址: ").strip()
    if not url:
        print("网址不能为空。")
        sys.exit(1)
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    username = input("账号: ").strip()
    password = getpass.getpass("密码: ")

    screen_name = input("输入画面名称: ").strip()

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError:
        print("当前 Python 环境里未安装 playwright。")
        print("请在与运行本脚本相同的解释器中执行（PowerShell 示例，一行一条）：")
        print("  python -m pip install playwright")
        print("  python -m playwright install chromium")
        print("若使用 venv，先执行 .\\venv\\Scripts\\activate 再安装；若有多版本 Python，请用 py -3.11 -m pip ... 指定版本。")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(60_000)

        try:
            page.goto(url, wait_until="domcontentloaded")

            try:
                page.locator("canvas").first.wait_for(state="visible", timeout=15_000)
            except Exception:
                pass

            page.locator('input.xl-input__inner[placeholder="请输入用户名"]').fill(username)
            page.locator('input.xl-input__inner[type="password"]').fill(password)

            captcha = _ocr_captcha_from_canvas(page)
            if captcha:
                print("识别到验证码:", captcha)
            if not captcha:
                captcha = input("请输入验证码（可对照浏览器中 canvas）: ").strip()

            page.get_by_placeholder("请输入验证码").fill(captcha)
            page.get_by_role("button", name="登录").click()
            page.wait_for_load_state("networkidle")

            try:
                page.locator('div.xr-menu[role="menu"]').first.wait_for(
                    state="visible",
                    timeout=60_000,
                )
            except Exception:
                print("未在 60s 内检测到侧栏菜单，跳过菜单步骤。")
            else:
                if screen_name:
                    print("点击画面:", screen_name)
                    _click_sidebar_label(page, screen_name)

            print("流程结束（请确认浏览器画面）。")
        except Exception as exc:  # noqa: BLE001
            print("执行出错:", exc)
            page.screenshot(path="auto_login_error.png", full_page=True)
            print("已保存截图: auto_login_error.png")
        finally:
            input("按回车关闭浏览器…")
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
