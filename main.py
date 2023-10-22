#!/usr/bin/env python3
import argparse
import logging
from datetime import timedelta, datetime
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
parser.add_argument(
    '-d', '--date',
    type=str,
    help='Date in past, reaching which parser would stop.'
         'Format [dd.mm.yyyy]. If not specified - set as week before.'
)


def main() -> None:
    args = parser.parse_args()
    from_date = get_stop_date(getattr(args, 'date'))

    results = {}

    with sync_playwright() as pw:
        log.info('processing social networks')

        for sn_name, func in sns.items():
            file_path = getattr(args, sn_name)
            account_list = file_to_acc_list(file_path)
            if not account_list:
                log.info(f'No [{sn_name}] accounts found in {file_path}')
                continue

            results[sn_name] = func(
                account_list=account_list,
                from_date=from_date,
                pw=pw
            )

    # TODO: data saving
    print(results)


def file_to_acc_list(file_path: Path) -> list[str]:
    account_list = []
    try:
        with open(file_path) as file:
            for acc in file.readlines():
                account_list.append(acc.strip())
    except Exception as e:
        log.debug(e)
    return account_list


def get_stop_date(date_str: str) -> datetime:
    """
    Get stop date from CLI argument.
    If blank or an error rises - defaults to week before today
    :param date_str: date in format dd.mm.yyyy from the CLI
    :return: datetime object
    """
    if date_str:
        try:
            # parse datetime from string
            stop_date = datetime.strptime(date_str, '%d.%m.%Y')
            return stop_date
        except Exception as e:
            log.error(f'Parsing date failed: input was "{date_str}"' + str(e))

    stop_date = datetime.now() - timedelta(days=7)
    log.info(f'Stop date set as {stop_date}')
    return stop_date


if __name__ == "__main__":
    main()
