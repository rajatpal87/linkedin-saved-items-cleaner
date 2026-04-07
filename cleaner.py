#!/usr/bin/env python3
"""
LinkedIn Saved Items Cleaner
Removes all saved jobs and saved posts/articles from your LinkedIn account.

Usage:
    python cleaner.py --login          # First run: opens browser for manual login
    python cleaner.py                  # Delete both saved jobs and saved posts
    python cleaner.py --jobs-only      # Delete only saved jobs
    python cleaner.py --posts-only     # Delete only saved posts/articles
"""

import asyncio
import argparse
import random
import sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

AUTH_FILE = Path(__file__).parent / "auth.json"
SAVED_JOBS_URL = "https://www.linkedin.com/my-items/saved-jobs/"
SAVED_POSTS_URL = "https://www.linkedin.com/my-items/saved-posts/"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login_and_save_session():
    """Open a visible browser for manual login, then save the session."""
    print("Opening browser for login...")
    print("Please log in to LinkedIn in the browser window that opens.")
    print("The script will wait until you reach your LinkedIn feed.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")

        print("Waiting for login... (up to 5 minutes)")
        try:
            await page.wait_for_url(
                lambda url: (
                    "linkedin.com/feed" in url
                    or ("linkedin.com/in/" in url and "login" not in url)
                ),
                timeout=300_000,
            )
        except PlaywrightTimeoutError:
            print("Timed out waiting for login. Please try again.")
            await browser.close()
            sys.exit(1)

        print("Login detected! Saving session...")
        await context.storage_state(path=str(AUTH_FILE))
        await browser.close()
        print(f"Session saved to {AUTH_FILE}")
        print("\nYou can now run the cleaner without --login:")
        print("  python cleaner.py")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def require_session():
    if not AUTH_FILE.exists():
        print("No saved session found. Run with --login first:")
        print("  python cleaner.py --login")
        sys.exit(1)


async def is_logged_in(page) -> bool:
    url = page.url
    if "linkedin.com/login" in url or "linkedin.com/authwall" in url:
        print("\nSession expired. Re-run with --login to log in again:")
        print("  python cleaner.py --login")
        return False
    return True


async def random_delay(min_s=1.0, max_s=2.5):
    await asyncio.sleep(random.uniform(min_s, max_s))


# ---------------------------------------------------------------------------
# Saved Jobs
# ---------------------------------------------------------------------------

async def unsave_all_jobs(page) -> int:
    """Navigate to saved jobs page and unsave every job. Returns count removed."""
    print(f"\n--- Saved Jobs ---")
    await page.goto(SAVED_JOBS_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if not await is_logged_in(page):
        return 0

    total = 0

    while True:
        # Target the save toggle on individual job cards.
        # These have aria-label like "Save job: Title at Company" and aria-pressed="true" when saved.
        # Exclude disabled buttons (the filter pill tab also has text "Saved" but is disabled).
        saved_buttons = await page.locator(
            'button[aria-label*="Save job" i][aria-pressed="true"]:not([disabled])'
        ).all()

        if not saved_buttons:
            # Fallback: aria-label containing "Unsave job"
            saved_buttons = await page.locator(
                'button[aria-label*="Unsave job" i]:not([disabled])'
            ).all()

        if not saved_buttons:
            print(f"No more saved jobs found. Removed {total} total.")
            break

        print(f"Found {len(saved_buttons)} saved job(s) on screen — unsaving...")
        for btn in saved_buttons:
            try:
                await btn.scroll_into_view_if_needed()
                await btn.click()
                total += 1
                delay = random.uniform(1.0, 2.5)
                print(f"  [{total}] Unsaved  (next in {delay:.1f}s)")
                await page.wait_for_timeout(int(delay * 1000))
            except Exception as e:
                print(f"  Skipping button (could not click): {e}")

        # Scroll to bottom to trigger loading of more items
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

    return total


# ---------------------------------------------------------------------------
# Saved Posts / Articles
# ---------------------------------------------------------------------------

async def _find_and_click_remove_in_menu(page) -> bool:
    """
    Look for the 'Unsave' item in LinkedIn's post dropdown.
    Returns True if clicked, False if not found.
    LinkedIn's dropdown uses non-semantic elements (no role="menuitem"),
    so we use text-based matching which works on any element type.
    """
    candidates = [
        page.get_by_text("Unsave", exact=True),
        page.get_by_text("Remove from saved", exact=False),
        page.get_by_role("menuitem").filter(has_text="Unsave"),
        page.get_by_role("menuitem").filter(has_text="Remove"),
        page.locator('li').filter(has_text="Unsave"),
        page.locator('li').filter(has_text="Remove from saved"),
    ]
    for locator in candidates:
        count = await locator.count()
        if count > 0:
            await locator.first.click()
            return True

    return False


async def unsave_all_posts(page) -> int:
    """Navigate to saved posts page and unsave every post/article. Returns count removed."""
    print(f"\n--- Saved Posts / Articles ---")
    await page.goto(SAVED_POSTS_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    if not await is_logged_in(page):
        return 0

    total = 0
    consecutive_failures = 0

    while True:
        # Each saved post card has a "more options" button (three-dot / ellipsis).
        # We find the first one, open it, and click "Remove from saved items".
        # Target only post-card action buttons.
        # Confirmed aria-label pattern: "Click to take more actions on [Name]'s post"
        # Must exclude the LinkedIn footer "More" nav button (aria-label='More options', text='More')
        more_buttons = await page.locator(
            'button[aria-label*="actions on" i]'
        ).all()

        if not more_buttons:
            print(f"No more saved posts found. Removed {total} total.")
            break

        btn = more_buttons[0]
        btn_label = await btn.get_attribute("aria-label") or ""
        try:
            await btn.scroll_into_view_if_needed()
            await btn.click()
            # Wait for the dropdown to actually appear in the DOM before querying items
            try:
                await page.wait_for_selector(
                    '[role="menu"], [role="menuitem"], .artdeco-dropdown__content',
                    timeout=3000,
                )
            except Exception:
                pass  # proceed anyway — some dropdowns use non-standard markup
            await page.wait_for_timeout(400)
        except Exception as e:
            print(f"  Could not open options menu: {e}")
            consecutive_failures += 1
            if consecutive_failures >= 5:
                print("  Too many failures. Stopping.")
                break
            continue

        removed = await _find_and_click_remove_in_menu(page)
        if removed:
            total += 1
            consecutive_failures = 0
            delay = random.uniform(1.0, 2.5)
            print(f"  [{total}] Removed  (next in {delay:.1f}s)")
            await page.wait_for_timeout(int(delay * 1000))
        else:
            # Close any open dropdown and skip this item (don't count as fatal failure)
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)
            consecutive_failures += 1
            print(f"  'Remove' not found in menu for: {btn_label!r}")
            if consecutive_failures >= 5:
                print("  Stopping — too many menus without a Remove option.")
                break

        # Scroll to bottom to trigger infinite scroll loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)

    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_cleaner(do_jobs: bool, do_posts: bool):
    require_session()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state=str(AUTH_FILE))
        page = await context.new_page()

        jobs_removed = 0
        posts_removed = 0

        if do_jobs:
            jobs_removed = await unsave_all_jobs(page)

        if do_posts:
            posts_removed = await unsave_all_posts(page)

        await browser.close()

    print("\n========== Summary ==========")
    if do_jobs:
        print(f"Saved jobs removed:   {jobs_removed}")
    if do_posts:
        print(f"Saved posts removed:  {posts_removed}")
    print("=============================")


def main():
    parser = argparse.ArgumentParser(
        description="Remove all saved jobs and saved posts/articles from LinkedIn."
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open browser for manual login and save session (run this first)",
    )
    parser.add_argument(
        "--jobs-only",
        action="store_true",
        help="Only remove saved jobs (skip saved posts/articles)",
    )
    parser.add_argument(
        "--posts-only",
        action="store_true",
        help="Only remove saved posts/articles (skip saved jobs)",
    )
    args = parser.parse_args()

    if args.login:
        asyncio.run(login_and_save_session())
        return

    do_jobs = not args.posts_only
    do_posts = not args.jobs_only

    if do_jobs and do_posts:
        target = "ALL saved jobs AND saved posts/articles"
    elif do_jobs:
        target = "ALL saved jobs"
    else:
        target = "ALL saved posts/articles"

    print(f"This will permanently unsave {target} from your LinkedIn account.")
    answer = input("Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        print("Aborted.")
        return

    asyncio.run(run_cleaner(do_jobs, do_posts))


if __name__ == "__main__":
    main()
