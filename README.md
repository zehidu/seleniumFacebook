# seleniumFacebook

Minimal Selenium (Python) project to automate Facebook login form interactions.

## Setup

1. Create a virtual environment and install deps:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
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

Windows PowerShell:

```powershell
$env:FB_EMAIL="you@example.com"
$env:FB_PASSWORD="your_password"
python run_login.py
```

Or prompt for credentials:

```bash
python run_login.py --prompt
```

## Notes

- If you have an old `chromedriver` in your system `PATH`, it can break runs with a `SessionNotCreatedException` due to version mismatch.
  - On Windows, this project hides any `chromedriver.exe` found in `PATH` by default so Selenium Manager can fetch the right version.
  - Set `SELENIUMFB_USE_PATH_CHROMEDRIVER=1` to force using the `PATH` driver.
- You can also put credentials in a local file that is **gitignored**:
  - Copy `config_local.py.example` to `config_local.py` and set `FB_EMAIL` / `FB_PASSWORD`.

Notes:
- Do **not** commit credentials to git.
- If you pasted your password into chat earlier, change it now.
