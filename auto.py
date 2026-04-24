# -*- coding: utf-8 -*-
"""
交互式登录 + 顶部全局搜索打开画面（Selenium + 本目录 chromedriver_2.exe + 本机 Chrome）：
  1) 网址、账号、密码均有默认值，回车即采用；canvas 验证码可 ddddocr 或手输
  2) 登录成功后先等待主壳加载，再顶部搜索打开画面；打开后等待业务页加载，再执行查询（F2查询 按钮或 F2 键）。

准备环境:
  pip install -r requirements-auto.txt

驱动: 优先 CHROMEDRIVER_PATH，其次同目录 chromedriver_2.exe / chromedriver.exe。
      若本地驱动与 Chrome 主版本不一致导致启动失败，会自动改用 Selenium 内置管理器下载匹配驱动（需外网）。
      无本地驱动时直接使用上述自动匹配。

可选环境变量:
  AUTO_POST_LOGIN_DWELL_SEC — 登录后 loading 结束再额外等待的秒数（默认 8，搜索索引慢可调大）。
  AUTO_SEARCH_MAX_RETRIES — 搜索无结果时清空重输的最大轮数（默认 15）。
  AUTO_OPENED_PAGE_DWELL_SEC — 打开业务页后 loading 结束再额外等待秒数（默认 3）。

DOM: div.header-search-trigger → 搜索输入框 → div.search-list-virtual span.search-item-title
"""

from __future__ import annotations

import getpass
import os
import sys
import time
from pathlib import Path

DEFAULT_URL = "http://10.81.73.9:10000/"
DEFAULT_USERNAME = "195141"
DEFAULT_PASSWORD = "LQ@1234321"


def _ensure_utf8_stdio() -> None:
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _resolve_chromedriver() -> Path | None:
    """若存在可用的本地驱动路径则返回；否则 None（由 Selenium Manager 自动解析）。"""
    env = os.environ.get("CHROMEDRIVER_PATH", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
    here = Path(__file__).resolve().parent
    for name in ("chromedriver_2.exe", "chromedriver.exe"):
        cand = here / name
        if cand.is_file():
            return cand
    return None


def _ocr_captcha_from_driver(driver) -> str | None:
    """对页面上「足够大」的可见 canvas 截图并 OCR；无 ddddocr 或失败则返回 None。"""
    try:
        import ddddocr
    except ImportError:
        print("未安装 ddddocr，将跳过自动识别。可执行: pip install ddddocr")
        return None

    from selenium.webdriver.common.by import By

    ocr = ddddocr.DdddOcr(show_ad=False)
    canvases = driver.find_elements(By.TAG_NAME, "canvas")
    best_png: bytes | None = None
    best_area = 0.0

    for c in canvases:
        if not c.is_displayed():
            continue
        try:
            size = c.size
            w, h = float(size["width"]), float(size["height"])
        except Exception:
            continue
        area = w * h
        if area < 1500:
            continue
        try:
            png = c.screenshot_as_png()
        except Exception:
            continue
        if area > best_area:
            best_area = area
            best_png = png

    if best_png is None:
        for c in canvases:
            if c.is_displayed():
                try:
                    best_png = c.screenshot_as_png()
                    break
                except Exception:
                    continue

    if not best_png:
        return None

    try:
        text = ocr.classification(best_png)
        return (text or "").strip()
    except Exception as exc:  # noqa: BLE001
        print("OCR 异常:", exc)
        return None


def _wait_post_login_loaded(driver, timeout: float = 120) -> None:
    """登录后主壳：document 完成、loading 消失；侧栏项足够多再额外静置（搜索索引常依赖菜单数据）。"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    w = WebDriverWait(driver, int(timeout))
    w.until(lambda d: d.execute_script("return document.readyState") == "complete")

    mask_selectors = (
        ".xl-loading-mask",
        ".el-loading-mask",
        ".el-loading-parent--relative .el-loading-mask",
        ".xl-loading-parent--relative .xl-loading-mask",
        "[class*='global-loading'][class*='mask']",
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        visible_mask = False
        for sel in mask_selectors:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    if el.is_displayed():
                        visible_mask = True
                        break
                except Exception:
                    continue
            if visible_mask:
                break
        if not visible_mask:
            break
        time.sleep(0.25)

    time.sleep(0.5)

    # 若存在侧栏，等待菜单节点达到一定数量（表示树数据已渲染，全局搜索常有依赖）
    try:
        sub_deadline = time.time() + 25
        while time.time() < sub_deadline:
            menus = driver.find_elements(By.CSS_SELECTOR, 'div.xr-menu[role="menu"]')
            if not menus or not menus[0].is_displayed():
                break
            n = len(
                menus[0].find_elements(
                    By.CSS_SELECTOR,
                    "li.xr-sub-menu, div.xr-sub-menu-content__title",
                ),
            )
            if n >= 5:
                break
            time.sleep(0.35)
    except Exception:
        pass

    # 额外静置：可通过环境变量 AUTO_POST_LOGIN_DWELL_SEC 调整（默认 8s）
    dwell = float(os.environ.get("AUTO_POST_LOGIN_DWELL_SEC", "8"))
    if dwell > 0:
        time.sleep(dwell)


def _open_screen_via_header_search(driver, query: str) -> None:
    """点击顶部搜索，输入关键词，在结果中选第一条（优先标题包含关键词）。"""
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    query = query.strip()
    if not query:
        return

    wait = WebDriverWait(driver, 60)
    trigger = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.header-search-trigger")),
    )
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        trigger,
    )
    trigger.click()
    time.sleep(0.35)

    input_el = None
    input_selectors = (
        (By.CSS_SELECTOR, "div[role='dialog'] input.xl-input__inner"),
        (By.CSS_SELECTOR, ".el-popper input.xl-input__inner"),
        (By.CSS_SELECTOR, "input.header-search-input"),
        (By.CSS_SELECTOR, ".header-search-popover input"),
        (By.CSS_SELECTOR, "input.xl-input__inner[placeholder*='搜索']"),
        (By.CSS_SELECTOR, "input.xl-input__inner[placeholder*='查']"),
    )
    for by, sel in input_selectors:
        try:
            el = WebDriverWait(driver, 4).until(EC.visibility_of_element_located((by, sel)))
            if el.is_displayed():
                input_el = el
                break
        except Exception:
            continue

    if input_el is None:
        for el in driver.find_elements(By.CSS_SELECTOR, "input.xl-input__inner"):
            try:
                ph = (el.get_attribute("placeholder") or "").strip()
                if not el.is_displayed():
                    continue
                if ph in ("请输入用户名", "请输入密码", "请输入验证码"):
                    continue
                input_el = el
                break
            except Exception:
                continue

    def _visible_search_titles():
        out = []
        for el in driver.find_elements(By.CSS_SELECTOR, "span.search-item-title"):
            try:
                if el.is_displayed() and el.text.strip():
                    out.append(el)
            except Exception:
                continue
        return out

    def _visible_no_match() -> bool:
        for xp in (
            "//*[contains(normalize-space(.),'无匹配')]",
            "//*[contains(normalize-space(.),'无相关数据')]",
        ):
            for el in driver.find_elements(By.XPATH, xp):
                try:
                    if el.is_displayed():
                        return True
                except Exception:
                    continue
        return False

    max_attempts = int(os.environ.get("AUTO_SEARCH_MAX_RETRIES", "15"))
    target_row = None
    chosen_title: str | None = None

    for attempt in range(max_attempts):
        if input_el is not None:
            input_el.click()
            time.sleep(0.1)
            input_el.clear()
            time.sleep(0.08)
            input_el.send_keys(query)
        else:
            ActionChains(driver).send_keys(query).perform()

        poll_end = time.time() + 28
        while time.time() < poll_end:
            titles = _visible_search_titles()
            if titles:
                break
            if _visible_no_match():
                time.sleep(0.55)
            time.sleep(0.4)

        titles = _visible_search_titles()
        for span in titles:
            try:
                t = span.text.strip()
                if query in t:
                    target_row = span.find_element(
                        By.XPATH,
                        "ancestor::div[contains(@class,'search-item')][1]",
                    )
                    chosen_title = t
                    break
            except Exception:
                continue

        if target_row is None and titles:
            try:
                span = titles[0]
                target_row = span.find_element(
                    By.XPATH,
                    "ancestor::div[contains(@class,'search-item')][1]",
                )
                chosen_title = span.text.strip()
            except Exception:
                target_row = None

        if target_row is not None:
            break

        if attempt < max_attempts - 1:
            wait_s = 1.5 + attempt * 0.5
            print(f"  搜索暂无有效结果，{wait_s:.1f}s 后重试输入 ({attempt + 1}/{max_attempts})…")
            time.sleep(wait_s)

    if target_row is None:
        raise RuntimeError(f"搜索「{query}」多次重试后仍无结果（可能索引未就绪或关键词不匹配）")

    if chosen_title:
        print("  将打开:", chosen_title)
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        target_row,
    )
    try:
        target_row.click()
    except Exception:
        driver.execute_script("arguments[0].click();", target_row)
    time.sleep(0.4)

    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(0.35)
    except Exception:
        pass


def _wait_opened_page_ready(driver, timeout: float = 120) -> None:
    """进入业务页后：readyState、loading 遮罩，再短静置（表格/查询区渲染）。"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    WebDriverWait(driver, int(timeout)).until(
        lambda d: d.execute_script("return document.readyState") == "complete",
    )

    mask_selectors = (
        ".xl-loading-mask",
        ".el-loading-mask",
        ".el-loading-parent--relative .el-loading-mask",
        ".xl-loading-parent--relative .xl-loading-mask",
        "[class*='global-loading'][class*='mask']",
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        visible_mask = False
        for sel in mask_selectors:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                try:
                    if el.is_displayed():
                        visible_mask = True
                        break
                except Exception:
                    continue
            if visible_mask:
                break
        if not visible_mask:
            break
        time.sleep(0.25)

    dwell = float(os.environ.get("AUTO_OPENED_PAGE_DWELL_SEC", "3"))
    if dwell > 0:
        time.sleep(dwell)


def _click_f2_query(driver) -> None:
    """点击左下角授权区「F2 查询」按钮（id 含 authButton-F2）；找不到再试文案/快捷键。"""
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    # 实际 DOM: div.left-auth-button-box.width-m > button#xxx-authButton-F2 > span.buttonNameBox{F2} + span{查询}
    locators: tuple[tuple[str, str], ...] = (
        (By.CSS_SELECTOR, "div.left-auth-button-box button[id*='authButton-F2']"),
        (By.CSS_SELECTOR, "button[id*='authButton-F2']"),
        (By.CSS_SELECTOR, "div.left-auth-button-box.width-m button"),
        (By.CSS_SELECTOR, "div.left-auth-button-box button"),
        (
            By.XPATH,
            "//div[contains(@class,'left-auth-button-box')]"
            "//button[.//span[contains(@class,'buttonNameBox')][normalize-space(.)='F2']]"
            "[.//span[normalize-space(.)='查询']]",
        ),
        (By.XPATH, "//button[contains(normalize-space(.),'F2查询')]"),
        (By.XPATH, "//button[contains(normalize-space(.),'F2') and contains(normalize-space(.),'查询')]"),
        (By.XPATH, "//span[contains(normalize-space(.),'F2查询')]/ancestor::button[1]"),
        (By.XPATH, "//span[contains(.,'F2') and contains(.,'查询')]/ancestor::button[1]"),
        (By.XPATH, "//button[contains(@class,'xl-button')][contains(.,'F2')][contains(.,'查询')]"),
    )
    for by, sel in locators:
        try:
            el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, sel)))
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                el,
            )
            el.click()
            bid = el.get_attribute("id") or ""
            print("  已点击查询:", ((el.text or "").strip() or bid)[:56])
            time.sleep(0.35)
            return
        except Exception:
            continue

    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()
        time.sleep(0.12)
        ActionChains(driver).send_keys(Keys.F2).perform()
        print("  已发送 F2 快捷键")
        time.sleep(0.35)
    except Exception as exc:
        raise RuntimeError("未找到「F2查询」按钮，且发送 F2 失败") from exc


def _click_login_button(driver) -> None:
    """点击登录按钮（兼容「登 录」中间空格、login-button 类名、xl/el 等）。"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    # 页面实际为 <button class="... login-button"><span>登 录</span></button>，中间为空白
    strip_login_xpath = (
        "//button[translate(normalize-space(.),"
        " ' \t\n\r\u00a0\u200b\u3000',"
        " '')='登录']"
    )

    locators: tuple[tuple[str, str], ...] = (
        (By.CSS_SELECTOR, "button.login-button"),
        (By.CSS_SELECTOR, "button.xl-button.submit.login-button"),
        (By.CSS_SELECTOR, "button.xl-button--primary.submit"),
        (By.XPATH, "//button[contains(@class,'login-button')]"),
        (By.XPATH, "//button[normalize-space(.)='登录']"),
        (By.XPATH, "//button[contains(normalize-space(.), '登录')]"),
        (By.XPATH, strip_login_xpath),
        (By.XPATH, "//span[normalize-space(.)='登 录']/ancestor::button[1]"),
        (By.XPATH, "//span[contains(normalize-space(.),'登') and contains(normalize-space(.),'录')]/ancestor::button[contains(@class,'login-button')][1]"),
        (By.XPATH, "//span[normalize-space(.)='登录']/ancestor::button[1]"),
        (By.XPATH, "//*[@role='button' and contains(normalize-space(.), '登录')]"),
        (By.XPATH, "//input[@type='submit' and contains(@value, '登录')]"),
        (By.XPATH, "//div[contains(@class,'xl-button') and contains(normalize-space(.), '登录')]"),
        (By.XPATH, "//div[contains(@class,'el-button') and contains(normalize-space(.), '登录')]"),
    )
    last_err: Exception | None = None
    for by, sel in locators:
        try:
            el = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((by, sel)),
            )
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                el,
            )
            el.click()
            return
        except Exception as e:
            last_err = e
    raise RuntimeError("未找到可点击的「登录」按钮") from last_err


def main() -> None:
    _ensure_utf8_stdio()

    url = input(f"访问网址 [回车默认 {DEFAULT_URL}]: ").strip() or DEFAULT_URL
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    username = input(f"账号 [回车默认 {DEFAULT_USERNAME}]: ").strip() or DEFAULT_USERNAME
    password = getpass.getpass("密码 [回车使用默认]: ").strip() or DEFAULT_PASSWORD

    screen_name = input("输入画面名称: ").strip()

    try:
        from selenium import webdriver
        from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ModuleNotFoundError:
        print("当前 Python 环境里未安装 selenium。")
        print("请执行: python -m pip install -r requirements-auto.txt")
        sys.exit(1)

    def _driver_version_mismatch(exc: BaseException) -> bool:
        msg = str(exc).lower()
        return (
            "session not created" in msg
            or "only supports chrome version" in msg
            or "chromedriver only supports" in msg
        )

    options = Options()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors=yes")
    local_driver = _resolve_chromedriver()
    driver = None
    try:
        if local_driver is not None:
            try:
                driver = webdriver.Chrome(
                    service=Service(executable_path=str(local_driver)),
                    options=options,
                )
            except SessionNotCreatedException:
                print(
                    "提示: 本地 ChromeDriver 与已安装 Chrome 主版本不一致，"
                    "已改用 Selenium 自动下载的驱动（需能访问外网）。",
                )
                driver = webdriver.Chrome(service=Service(), options=options)
            except WebDriverException as e:
                if _driver_version_mismatch(e):
                    print(
                        "提示: 本地 ChromeDriver 与已安装 Chrome 主版本不一致，"
                        "已改用 Selenium 自动下载的驱动（需能访问外网）。",
                    )
                    driver = webdriver.Chrome(service=Service(), options=options)
                else:
                    raise
        else:
            driver = webdriver.Chrome(service=Service(), options=options)
    except Exception as exc:  # noqa: BLE001
        print("无法启动 Chrome:", exc)
        if local_driver is not None:
            print(
                "可删除或重命名同目录 chromedriver_2.exe 后重试，"
                "或从 https://googlechromelabs.github.io/chrome-for-testing/ 下载与 Chrome 主版本一致的驱动。",
            )
        sys.exit(1)

    driver.set_page_load_timeout(120)
    wait = WebDriverWait(driver, 60)

    try:
        driver.get(url)

        try:
            wait.until(EC.visibility_of_element_located((By.TAG_NAME, "canvas")))
        except Exception:
            pass

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input.xl-input__inner[placeholder="请输入用户名"]'),
            ),
        )
        user_el = driver.find_element(
            By.CSS_SELECTOR,
            'input.xl-input__inner[placeholder="请输入用户名"]',
        )
        user_el.clear()
        user_el.send_keys(username)
        pwd_el = driver.find_element(
            By.CSS_SELECTOR,
            'input.xl-input__inner[type="password"]',
        )
        pwd_el.clear()
        pwd_el.send_keys(password)

        captcha = _ocr_captcha_from_driver(driver)
        if captcha:
            print("识别到验证码:", captcha)
        if not captcha:
            captcha = input("请输入验证码（可对照浏览器中 canvas）: ").strip()

        cap_el = driver.find_element(
            By.CSS_SELECTOR,
            'input.xl-input__inner[placeholder="请输入验证码"]',
        )
        cap_el.clear()
        cap_el.send_keys(captcha)

        _click_login_button(driver)

        try:
            WebDriverWait(driver, 120).until(
                EC.any_of(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "div.header-search-trigger"),
                    ),
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'div.xr-menu[role="menu"]'),
                    ),
                ),
            )
        except Exception:
            print("未在 120s 内检测到主界面（顶部搜索或侧栏），跳过打开画面。")
        else:
            if screen_name:
                print("等待主界面加载完成后再打开搜索…")
                _wait_post_login_loaded(driver, timeout=120)
                print("顶部搜索打开画面:", screen_name)
                _open_screen_via_header_search(driver, screen_name)
                print("等待业务页加载完成…")
                _wait_opened_page_ready(driver, timeout=120)
                print("执行查询…")
                _click_f2_query(driver)

        print("流程结束（请确认浏览器画面）。")
    except Exception as exc:  # noqa: BLE001
        print("执行出错:", exc)
        try:
            driver.save_screenshot("auto_login_error.png")
            print("已保存截图: auto_login_error.png")
        except Exception:
            pass
    finally:
        if driver is not None:
            input("按回车关闭浏览器…")
            driver.quit()


if __name__ == "__main__":
    main()
