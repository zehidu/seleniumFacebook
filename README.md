# seleniumFacebook

Minimal Selenium (Python) project to automate Facebook login form interactions.

## Setup

1. Create a virtual environment and install deps:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Ensure **Google Chrome** is installed.

Selenium 4.6+ uses **Selenium Manager** to automatically download a matching **chromedriver** (no local driver path needed).

## Run

Recommended (does not store credentials in code/history):

```bash
export FB_EMAIL="you@example.com"
export FB_PASSWORD="your_password"
python run_login.py
```

Or prompt for credentials:

```bash
python run_login.py --prompt
```

Notes:
- Do **not** commit credentials to git.
- If you pasted your password into chat earlier, change it now.

