# LinkedIn Saved Items Cleaner

A simple script that removes all your saved jobs and saved posts/articles from LinkedIn in one go.

LinkedIn doesn't give you a "clear all" button — this script does that for you.

---

## What it does

- Removes all **saved jobs** from your LinkedIn account
- Removes all **saved posts and articles** from your LinkedIn account
- Opens a real browser window so you can see it working
- Adds random delays between actions to avoid triggering LinkedIn's rate limits

---

## Requirements

- Python 3.8 or higher
- A LinkedIn account

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/rajatpal87/linkedin-saved-items-cleaner.git
cd linkedin-saved-items-cleaner
```

**2. Create a virtual environment and install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

---

## Usage

**Step 1 — Log in (first time only)**
```bash
python cleaner.py --login
```
This opens a browser window. Log in to LinkedIn manually. Once you reach your feed, the script saves your session to `auth.json` and closes the browser. You only need to do this once (or whenever your session expires).

**Step 2 — Run the cleaner**
```bash
# Remove both saved jobs and saved posts
python cleaner.py

# Remove only saved jobs
python cleaner.py --jobs-only

# Remove only saved posts/articles
python cleaner.py --posts-only
```

You'll be asked to type `yes` to confirm before anything is deleted.

---

## Important notes

- `auth.json` stores your LinkedIn session and is excluded from this repo (via `.gitignore`). Never share this file.
- The script will not touch anything other than your saved items — it does not post, message, or interact with other accounts.
- If LinkedIn updates their page layout, selectors may need updating. Open an issue if the script stops working.

---

## How it works

The script uses [Playwright](https://playwright.dev/python/) to control a Chromium browser. It navigates to your saved jobs and saved posts pages, finds the relevant buttons, and clicks them — the same way you would manually, just faster.

---

## License

MIT — free to use and modify.
