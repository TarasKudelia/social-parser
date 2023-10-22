import logging
import re
from dataclasses import dataclass
from datetime import datetime

from playwright.sync_api import Page, Playwright, Locator


IG_ROOT_URL = 'https://www.instagram.com/'

log = logging.getLogger('sn-parse')


# page.screenshot(path="screenshot.png")

@dataclass
class IGAccPage:
    acc_name: str
    page: Page
    metadata: list
    is_ok: bool


def extract_header_data(header_locator: Locator) -> dict:
    """
    Extracts number of Posts, Followers and Following for the IG account,
    given valid header Locator
    :param header_locator:
    :return: dict with {posts, followers, following}
    """
    posts = None
    followers = None
    following = None

    header_list = header_locator.locator("ul").locator('li').all()
    for element in header_list:
        numb, text = element.text_content().split(' ')
        if text == 'followers' and not followers:
            el_html_str = element.inner_html()
            title_ = 'title="'
            start = el_html_str.find(title_) + len(title_)
            end = el_html_str.find('"', start=start)
            followers = el_html_str[start:end]
            continue

        # TODO: posts, following

    return {
        'posts': posts,
        'followers': followers,
        'following': following,
    }


def get_account_with_retries(page, acc_to_scrape, retries: int) -> IGAccPage:
    # Get Account data
    meta_data = None
    is_ok = False

    for i in range(retries):
        page.goto(IG_ROOT_URL + acc_to_scrape)
        try:
            header = page.locator("header")
            res = header.wait_for(timeout=5_000)
            if header.is_enabled():
                IGAccPage(acc_to_scrape, page, meta_data, True)

        except Exception as te:
            retries -= 1
            # Detect "Smth went wrong"
            page_title = page.locator('title').first().inner_text()
            clean_title = re.compile('[^a-zA-Z ]').sub('', page_title)
            if clean_title.startswith('Page couldnt load'):
                if not meta_data:
                    meta = page.locator('head').locator('meta').all()
                    if not meta:
                        continue
                    meta_data = meta
            page.reload()

    return IGAccPage(acc_to_scrape, page, meta_data, is_ok)


def ig_parse(account_list, pw: Playwright, from_date: datetime):
    # Emulate IPhone 8 platform to minimize IG scrape blocking
    iphone_8 = pw.devices['iPhone 8']

    browser = pw.chromium.launch()
    context = browser.new_context(**iphone_8)
    page = context.new_page()

    accounts_scraped = {}

    for acc_to_scrape in account_list:
        log.info(f'Start processing: "{acc_to_scrape}"')

        retries = 10
        acc_result = get_account_with_retries(page, acc_to_scrape, retries)
        if not acc_result.is_ok:
            reason = f"After {retries} retries, account page couldn't be loaded"
            log.info(reason)
            accounts_scraped[acc_to_scrape] = {
                'error': reason
            }
            continue

        # Acc page loaded as expected
        header = page.locator("header")
        header_data = extract_header_data(header)

        ...
        # Get latest posts


def login(page, ig_user, ig_pass) -> bool:
    """
    Automates login form pass-through.

    :param page: Playwright page
    :param ig_user: username for an IG account
    :param ig_pass: password for an IG account
    :return: True if login performed
    """
    login_form = page.get_by_label("Phone number, username, or email")
    if not login_form.is_enabled():
        return False

    login_form.fill(ig_user)
    page.get_by_label("Password").fill(ig_pass)
    page.get_by_role("button", name="Log in", exact=True).click()

    notif_window = page.get_by_role("button", name="Not Now")
    if notif_window.is_visible():
        notif_window.click()

    return True
