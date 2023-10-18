import logging
import re
from dataclasses import dataclass
from datetime import datetime
import os
from dotenv import load_dotenv
from playwright.sync_api import Page, Playwright, Locator


IG_ROOT_URL = 'https://www.instagram.com/'
IG_TITLE_COULD_NOT_LOAD = 'Page couldnt load'
IG_TITLE_LOGIN = 'Login  Instagram'

log = logging.getLogger('sn-parse')
# page.screenshot(path="screenshot.png")

load_dotenv('cfg.env')
IG_USER = os.getenv('IG_USER')
IG_PASS = os.getenv('IG_PASS')


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


def extract_posts_with_scrolling(
        page: Page,
        post_container: Locator,
        from_date: datetime
) -> dict:
    post_data = {}

    # get div with post rows
    post_rows = post_container.first.first

    last_date = datetime.now()

    # scroll to spawn posts on event
    while last_date > from_date:
        page.mouse.wheel(0, 100)
        # if is_for_login_overlay(page):
        #     remove_overlay_from_dom(page)
        # last_date = get_last_post_date(post_rows)

    # update html
    post_rows = post_container.first.first.all()
    for row in post_rows:
        # parse_post_row(post_data, row)
        ...
    return post_data


def get_account_posts_with_retries(
        page,
        acc_to_scrape,
        retries: int,
        from_date: datetime
) -> dict:
    # Get Account data
    post_data = None
    meta_data = None
    errors = []

    page.goto(IG_ROOT_URL + acc_to_scrape)
    for i in range(retries):
        try:
            # try get header
            header = page.locator("header")
            header.wait_for(timeout=1_000)
            if header.is_enabled():
                # Acc page loaded as expected
                header_data = extract_header_data(header)

                post_container = page.locator('article')
                post_container.wait_for(timeout=5_000)
                if not post_container.is_visible():
                    reason = 'Container with posts not loaded for 10 sec.'
                    log.info(reason)
                    errors.append(reason)
                    continue

                post_data = extract_posts_with_scrolling(post_container, from_date)
                break

        except Exception as te:
            # If we catch "something went wrong" page
            title_elem = page.locator('title')
            page_title = title_elem.all()[0].inner_text()
            clean_title = re.compile('[^a-zA-Z ]').sub('', page_title)

            if not meta_data:
                if clean_title.startswith(IG_TITLE_COULD_NOT_LOAD):
                    meta = page.locator('head').locator('meta').all()
                    if meta:
                        meta_data = meta
                        # TODO: extract metadata here

    return {
        "post_data": post_data,
        "meta_data": meta_data,
        "errors": errors
    }


def get_last_post_pub_date():
    # TODO
    pass


def ig_parse(
        account_list,
        pw: Playwright,
        from_date: datetime,
        headless=False,
        **kwargs
):
    # Emulate IPhone 8 platform to minimize IG scrape blocking
    # iphone_8 = pw.devices['iPhone 8']

    browser = pw.firefox.launch(headless=headless)
    context = browser.new_context()  # **iphone_8
    page = context.new_page()
    # page.set_extra_http_headers(IG_HEADERS)

    accounts_scraped = {}

    for acc_to_scrape in account_list:
        log.info(f'Start processing: "{acc_to_scrape}"')

        retries = 10
        acc_result = get_account_posts_with_retries(page, acc_to_scrape,
                                                    retries)
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

        post_container = page.locator('article')
        post_container.wait_for(timeout=10_000)
        if not post_container.is_visible():
            reason = 'Container with posts not loaded for 10 sec.'
            log.info(reason)
            accounts_scraped[acc_to_scrape] = {
                'error': reason
            }
            continue

        latest_date = get_last_post_pub_date()
        if latest_date <= from_date:
            # no new posts
            reason = 'no new posts'
            log.info(reason)
            accounts_scraped[acc_to_scrape] = {
                'info': reason
            }
            continue
        # Get latest posts


def login(page, ig_user, ig_pass) -> bool:
    """
    Automates login form pass-through.

    :param page: Playwright page
    :param ig_user: username for an IG account
    :param ig_pass: password for an IG account
    :return: page with performed login, or None on error
    """
    login_form = page.get_by_label("Phone number, username, or email")
    if not login_form.is_enabled():
        return None

    login_form.fill(ig_user)
    page.get_by_label("Password").fill(ig_pass)
    page.get_by_role("button", name="Log in", exact=True).click()

    notif_window = page.get_by_role("button", name="Not Now")
    if notif_window.is_visible():
        notif_window.click()

    return page
