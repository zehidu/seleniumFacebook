#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import sys
import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import fb_selectors as sel


def find_first(driver, locators: list[tuple[str, str]], timeout_s: float = 20.0):
    """Try multiple locators until one matches (polling)."""
    end = None if timeout_s <= 0 else time.time() + timeout_s
    last_exc: Optional[Exception] = None
    while end is None or time.time() < end:
        for by, value in locators:
            try:
                return driver.find_element(by, value)
            except Exception as exc:
                last_exc = exc
        time.sleep(0.2)
    raise RuntimeError(f"Timed out finding any of: {locators}") from last_exc


def xpath_literal(s: str) -> str:
    # Safe quoting for XPath string literals.
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    parts = s.split("'")
    expr_parts: list[str] = []
    for i, part in enumerate(parts):
        expr_parts.append(f"'{part}'")
        if i != len(parts) - 1:
            expr_parts.append("\"'\"")
    return "concat(" + ", ".join(expr_parts) + ")"


def safe_click(driver, el) -> bool:
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            el,
        )
    except Exception:
        pass

    try:
        el.click()
        return True
    except Exception:
        pass

    try:
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        return False


def element_exists(driver, by: str, value: str) -> bool:
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False
    except Exception:
        return False


def wait_for_home_menu(driver, menu_locators: list[tuple[str, str]], timeout_s: float, give_up_login_page_after_s: float = 15.0):
    """Wait for the logged-in home UI indicator (Menu button).

    If we stay on the login form too long, assume login failed and stop early.
    """
    end = None if timeout_s <= 0 else time.time() + timeout_s
    start = time.time()
    while end is None or time.time() < end:
        for by, value in menu_locators:
            try:
                return driver.find_element(by, value)
            except Exception:
                pass

        if time.time() - start >= give_up_login_page_after_s:
            if "login" in (driver.current_url or "") and element_exists(driver, By.CSS_SELECTOR, "form[data-testid='royal_login_form']"):
                return None

        time.sleep(0.2)
    return None


def click_cookie_banners(driver):
    # Best-effort: banner text varies by region/language.
    xpaths = [
        "//button[contains(., 'Allow all cookies')]",
        "//button[contains(., 'Allow essential and optional cookies')]",
        "//button[contains(., 'Only allow essential cookies')]",
        "//button[contains(., 'Accept all')]",
        "//button[contains(., 'Accept')]",
        "//*[@role='button' and contains(., 'Allow all cookies')]",
        "//*[@role='button' and contains(., 'Accept')]",
    ]
    for xp in xpaths:
        try:
            btn = driver.find_element(By.XPATH, xp)
        except NoSuchElementException:
            continue
        try:
            btn.click()
            return True
        except Exception:
            continue
    return False


def build_chrome(headless: bool):
    # If a stale chromedriver.exe is present in PATH on Windows, Selenium Manager may
    # pick it up and fail with "only supports Chrome version X". We hide any
    # chromedriver found in PATH for this process so Selenium Manager can download
    # a matching driver automatically.
    if (
        os.name == "nt"
        and os.environ.get("SELENIUMFB_USE_PATH_CHROMEDRIVER", "").strip()
        not in {"1", "true", "TRUE", "yes", "YES"}
    ):
        exe = "chromedriver.exe" if os.name == "nt" else "chromedriver"
        path_entries = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        kept: list[str] = []
        removed: list[str] = []
        for entry in path_entries:
            entry_clean = entry.strip().strip('"')
            try:
                if (Path(entry_clean) / exe).exists():
                    removed.append(entry_clean)
                    continue
            except Exception:
                # If the path entry is malformed/unreadable, keep it.
                pass
            kept.append(entry)

        if removed:
            os.environ["PATH"] = os.pathsep.join(kept)
            print(
                "Ignoring chromedriver found in PATH (will use Selenium Manager instead). "
                "Set SELENIUMFB_USE_PATH_CHROMEDRIVER=1 to override.",
                file=sys.stderr,
            )

    opts = ChromeOptions()
    if headless:
        # Works on recent Chrome versions; if it fails, try "--headless" instead.
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1280,900")

    # Good defaults for CI/containers; generally harmless on desktop.
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")

    # Optional: allow overriding the Chrome binary if needed.
    chrome_bin = os.environ.get("CHROME_BINARY", "").strip()
    if chrome_bin:
        opts.binary_location = chrome_bin

    # Do NOT pass a chromedriver path: Selenium Manager will download/resolve it.
    return webdriver.Chrome(options=opts)


def wait_for_post_login(driver, initial_url: str, timeout_s: float):
    end = time.time() + timeout_s
    while time.time() < end:
        if driver.get_cookie("c_user") is not None:
            return True
        if driver.current_url != initial_url:
            return True
        time.sleep(0.2)
    return False


def load_credentials(args) -> tuple[str, str]:
    email = os.environ.get("FB_EMAIL", "").strip()
    password = os.environ.get("FB_PASSWORD", "")

    # Optional local file (gitignored): config_local.py
    try:
        import config_local  # type: ignore

        email = (getattr(config_local, "FB_EMAIL", "") or email).strip()
        password = getattr(config_local, "FB_PASSWORD", "") or password
    except Exception:
        pass

    if args.email:
        email = args.email.strip()
    if args.password:
        password = args.password

    if args.prompt:
        if not email:
            email = input("Facebook email/phone: ").strip()
        if not password:
            password = getpass.getpass("Facebook password: ")

    return email, password


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://www.facebook.com/", help="URL to open")
    ap.add_argument("--headless", action="store_true", help="Run headless")
    ap.add_argument("--timeout", type=float, default=20.0, help="Element wait timeout (seconds)")
    ap.add_argument("--post-timeout", type=float, default=30.0, help="Post-login wait timeout (seconds)")
    ap.add_argument(
        "--home-timeout",
        type=float,
        default=300.0,
        help="Wait for home UI to appear (menu button). 0 = wait forever",
    )
    ap.add_argument(
        "--menu-label",
        default="Menu",
        help="aria-label for the home menu button (locale dependent). Default: Menu",
    )
    ap.add_argument("--email", help="Email/phone (prefer env var FB_EMAIL)")
    ap.add_argument(
        "--password",
        help="Password (prefer env var FB_PASSWORD; passing via CLI is insecure)",
    )
    ap.add_argument("--prompt", action="store_true", help="Prompt for missing credentials")
    menu_group = ap.add_mutually_exclusive_group()
    menu_group.add_argument(
        "--open-menu",
        dest="open_menu",
        action="store_true",
        default=None,
        help="Open the home Menu button after login (default)",
    )
    menu_group.add_argument(
        "--no-open-menu",
        dest="open_menu",
        action="store_false",
        default=None,
        help="Do not click the home Menu button",
    )
    keep_group = ap.add_mutually_exclusive_group()
    keep_group.add_argument(
        "--keep-open",
        dest="keep_open",
        action="store_true",
        default=None,
        help="Keep browser open until Enter is pressed (default when not headless)",
    )
    keep_group.add_argument(
        "--auto-close",
        dest="keep_open",
        action="store_false",
        default=None,
        help="Close browser automatically when done (default when headless)",
    )
    ap.add_argument("--screenshot-after", type=Path, help="Write a screenshot after login attempt")
    args = ap.parse_args(argv)

    keep_open = args.keep_open
    if keep_open is None:
        keep_open = not args.headless

    open_menu = args.open_menu
    if open_menu is None:
        open_menu = True

    email, password = load_credentials(args)
    if not email or not password:
        print(
            "Missing credentials. Use FB_EMAIL/FB_PASSWORD env vars, config_local.py, or --prompt.",
            file=sys.stderr,
        )
        return 2

    driver = build_chrome(headless=args.headless)
    try:
        driver.get(args.url)
        click_cookie_banners(driver)

        # Wait for login form/inputs.
        find_first(driver, sel.LOGIN_FORM, timeout_s=args.timeout)
        email_el = find_first(driver, sel.EMAIL_INPUT, timeout_s=args.timeout)
        pass_el = find_first(driver, sel.PASSWORD_INPUT, timeout_s=args.timeout)

        email_el.clear()
        email_el.send_keys(email)
        pass_el.clear()
        pass_el.send_keys(password)

        initial_url = driver.current_url

        # Submit via Enter on password field.
        pass_el.send_keys(Keys.ENTER)

        wait_for_post_login(driver, initial_url=initial_url, timeout_s=args.post_timeout)

        # Manual checkpoint/CAPTCHA may appear after login. We just wait until the
        # logged-in UI shows up (menu button), then optionally click it.
        if open_menu:
            label = (args.menu_label or "").strip()
            menu_locators = []
            if label:
                menu_locators.append((By.XPATH, f"//*[@role='button' and @aria-label={xpath_literal(label)}]"))
            menu_locators.extend(sel.HOME_MENU_BUTTON)

            menu_btn = wait_for_home_menu(driver, menu_locators, timeout_s=args.home_timeout)
            if menu_btn is None:
                print(
                    "Home menu button not found (still on checkpoint/robot detection?).",
                    file=sys.stderr,
                )
            else:
                expanded = (menu_btn.get_attribute("aria-expanded") or "").lower()
                if expanded != "true":
                    safe_click(driver, menu_btn)

        if args.screenshot_after:
            args.screenshot_after.parent.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(args.screenshot_after))

        print(driver.current_url)

        if keep_open:
            input("Press Enter to close the browser...")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
