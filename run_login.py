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
    end = time.time() + timeout_s
    last_exc: Optional[Exception] = None
    while time.time() < end:
        for by, value in locators:
            try:
                return driver.find_element(by, value)
            except Exception as exc:
                last_exc = exc
        time.sleep(0.2)
    raise RuntimeError(f"Timed out finding any of: {locators}") from last_exc


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
    ap.add_argument("--email", help="Email/phone (prefer env var FB_EMAIL)")
    ap.add_argument(
        "--password",
        help="Password (prefer env var FB_PASSWORD; passing via CLI is insecure)",
    )
    ap.add_argument("--prompt", action="store_true", help="Prompt for missing credentials")
    ap.add_argument("--keep-open", action="store_true", help="Keep browser open until Enter is pressed")
    ap.add_argument("--screenshot-after", type=Path, help="Write a screenshot after login attempt")
    args = ap.parse_args(argv)

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

        if args.screenshot_after:
            args.screenshot_after.parent.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(args.screenshot_after))

        print(driver.current_url)

        if args.keep_open:
            input("Press Enter to close the browser...")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
