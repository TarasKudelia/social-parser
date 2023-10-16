#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright
from parsers.instagram import ig_parse
from parsers.youtube import yt_parse


log = logging.getLogger(__name__)

# list_of_YT_accs = [
#     '@StratEdgyProductions',
#     '@MrBeast',
#     '@UnusualVideos',
#     '@DEFCONConference',
# ]
list_of_IG_accs = [
    # 'arianagrande',
    # 'nasa',
    # 'nike',
    'siriy_ua',
]

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

    # process YT
    yt_acc_file = args.youtube
    yt_accs = file_to_acc_list(yt_acc_file)
    if not yt_accs:
        log.debug(f'No Youtube accounts provided or found in {yt_acc_file}')

    results = {}
    with sync_playwright() as pw:
        log.info('Do work')

        if yt_accs:
            results['youtube'] = yt_parse(yt_accs)

        # if ig_acccs:
        #     results['instagram'] = ig_parse(pw)
    print(results)


if __name__ == "__main__":
    main()
