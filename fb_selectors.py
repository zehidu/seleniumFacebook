from __future__ import annotations

from selenium.webdriver.common.by import By

# These are based on the HTML you provided for the Facebook login form.
# Keep selectors stable (prefer id/name/data-testid) and avoid brittle classes.

LOGIN_FORM = [
    (By.CSS_SELECTOR, "form[data-testid='royal_login_form']"),
    (By.CSS_SELECTOR, "form[data-testid='royal_login_form'] input#email"),
    (By.ID, "login_form"),  # sometimes used on /login.php
]

EMAIL_INPUT = [
    (By.ID, "email"),
    (By.CSS_SELECTOR, "input[data-testid='royal-email']"),
    (By.CSS_SELECTOR, "input[name='email']"),
]

PASSWORD_INPUT = [
    (By.ID, "pass"),
    (By.CSS_SELECTOR, "input[data-testid='royal-pass']"),
    (By.CSS_SELECTOR, "input[name='pass']"),
]

LOGIN_SUBMIT = [
    (By.CSS_SELECTOR, "button[data-testid='royal-login-button']"),
    (By.CSS_SELECTOR, "button[name='login'][type='submit']"),
    (By.ID, "loginbutton"),  # sometimes used on /login.php
]

# Logged-in home UI
HOME_MENU_BUTTON = [
    # This is the grid/menu button on the top bar after login (English locale).
    (By.CSS_SELECTOR, "div[role='button'][aria-label='Menu']"),
    (By.XPATH, "//*[@role='button' and @aria-label='Menu']"),
]

MARKETPLACE_ENTRY = [
    # Prefer href-based matches (more stable than classes).
    (By.CSS_SELECTOR, "a[href*='/marketplace']"),
    (By.CSS_SELECTOR, "a[href*='facebook.com/marketplace']"),
    (By.XPATH, "//a[contains(@href, '/marketplace') or contains(@href, 'facebook.com/marketplace')]"),
    # Fallback: locate by visible text.
    (By.XPATH, "//span[normalize-space()='Marketplace']/ancestor::*[self::a or @role='link' or @role='button'][1]"),
]
