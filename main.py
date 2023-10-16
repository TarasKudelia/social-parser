#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright
from parsers.instagram import ig_parse
from parsers.youtube import yt_parse


log = logging.getLogger(__name__)

sns = {
    'youtube': yt_parse,
    'instagram': ig_parse,
}


# Setting up args parser
parser = argparse.ArgumentParser(
    prog='SocialParser',
    description='Parses specified SN`s from list of accounts',
    epilog='Text at the bottom of help'
)
parser.add_argument(
    '-ig', '--instagram',
    type=Path,
    help='List of Instagram accounts, text file.'
)
parser.add_argument(
    '-yt', '--youtube',
    type=Path,
    help='List of YouTube accounts, text file.'
)


def file_to_acc_list(file_path: Path) -> list[str]:
    account_list = []
    try:
        with open(file_path) as file:
            for acc in file.readlines():
                account_list.append(acc.strip())
    except Exception as e:
        log.debug(e)
    return account_list


def main() -> None:
    args = parser.parse_args()

    results = {}

    with sync_playwright() as pw:
        log.info('processing social networks')
        browser = pw.chromium.launch()

        for sn_name, func in sns.items():
            file_path = getattr(args, sn_name)
            account_list = file_to_acc_list(file_path)
            if not account_list:
                log.info(f'No [{sn_name}] accounts found in {file_path}')
                continue

            results[sn_name] = func(account_list, browser=browser)

    # TODO: data saving
    print(results)


if __name__ == "__main__":
    main()
