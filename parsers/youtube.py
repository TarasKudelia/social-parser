import datetime
import json
import logging
import re

import requests
from bs4 import BeautifulSoup, SoupStrainer
from playwright.sync_api import Playwright


YT_ROOT_URL = 'https://www.youtube.com/'
YT_CHANNEL_VIDS_URL = YT_ROOT_URL + '{}/videos'
YT_VIDEO_URL = YT_ROOT_URL + 'watch?v={}'

log = logging.getLogger(__name__)


def yt_parse(user_list, pw: Playwright = None, as_string=True) -> dict or str:
    log.debug(f'[YT] Recieved account file: {user_list}')
    parsed_vids = {}

    page = None
    if pw:
        browser = pw.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

    new_video_ids = ChannelParser.get_new_videos(user_list, page=page)
    for channel_id, ch_data in new_video_ids.items():
        vid_stats = {}
        # TODO -  if Account.get(k).not_exists() >> Account().create()
        vids = ch_data['latest_vids']

        for vid_id in vids:
            vid_stats[vid_id] = VideoDataParser.get_video_metrics(vid_id)
        parsed_vids[channel_id] = vid_stats

    if not as_string:
        return parsed_vids

    parsed_json = json.JSONEncoder().encode(parsed_vids)
    return parsed_json


def _filter_video_elements(element):
    """
    <a id="thumbnail" class="yt-simple-endpoint inline-block style-scope
    ytd-thumbnail" aria-hidden="true" tabindex="-1" rel="null"
    href="/watch?v=FqDTU0EAjok">
    """
    is_valid = element.name == 'script' and 'var ytInitialData' in str(element)
    return is_valid


def _filter_vid_details(script):
    return script.name == 'script' and 'videoDetails' in script.text


class ChannelParser:
    @staticmethod
    def _parse_acc_data(json_data: dict, errors: dict = None) -> dict or None:
        try:
            channel_metadata = json_data['metadata']['channelMetadataRenderer']
            return {
                'title': channel_metadata['title'],
                'external_id': channel_metadata['externalId'],
                'vanity_id': channel_metadata['vanityChannelUrl'],
                'channel_url': channel_metadata['channelUrl']
            }
        except Exception as e:
            errors['acc_data'] = {'error': repr(e)}
        return None

    @staticmethod
    def _get_videos_json(account_id) -> dict:
        channel_vids_url = YT_CHANNEL_VIDS_URL.format(account_id)
        resp = requests.get(channel_vids_url)
        bs = BeautifulSoup(resp.text, "lxml", parse_only=SoupStrainer('body'))
        initial_data = bs.find(_filter_video_elements).text
        data_json = json.loads(initial_data[initial_data.find('{') - 1:-1])
        return data_json

    @staticmethod
    def _get_videos_json_pw(page, account_id) -> dict:
        # TODO: enable if problems with loading all videos encountered
        channel_vids_url = YT_CHANNEL_VIDS_URL.format(account_id.strip())
        page.goto(channel_vids_url)
        body_scripts_locator = page.locator('body').locator('script').all()
        for script in body_scripts_locator:
            in_txt = script.inner_text()
            if in_txt.startswith('var ytInitialData'):
                return json.loads(in_txt[in_txt.find('{') - 1:-1])
        return None

    @staticmethod
    def _parse_tabs(videos_data, errors: dict = None) -> dict or KeyError:
        tab_layout = videos_data['contents']['twoColumnBrowseResultsRenderer']
        tabs = tab_layout['tabs']

        for tab in tabs:
            vid_data = []
            cont_data = None

            try:
                tab_data = tab['tabRenderer']['content']
                grid_data = tab_data['richGridRenderer']['contents']
                for grid_item in grid_data:
                    item_render = grid_item.get('richItemRenderer', None)
                    if item_render:
                        vid_data.append(
                            item_render['content']['videoRenderer']['videoId']
                        )
                    elif grid_item.get('continuationItemRenderer', None):
                        cont_data = grid_item['continuationItemRenderer']
                return {
                    'latest_vids': vid_data,
                    'cont_data': cont_data
                }
            except KeyError as e:
                if errors:
                    errors['parse_tabs']: repr(e)
        return None

    @staticmethod
    def get_new_videos(account_list: list[str],
                       page=None,
                       start_date: datetime = None,
                       stop_date: datetime = None,
                       max_amount: int = 30,
                       last_vid_id: str = None
                       ) -> dict:
        result = {}
        for acc in account_list:
            errors = {}
            try:
                if page:
                    vids_json = ChannelParser._get_videos_json_pw(page, acc)
                else:
                    vids_json = ChannelParser._get_videos_json(acc)
            except Exception as e:
                errors['request']: repr(e)
                continue

            # Good ending
            result[acc] = {
                'channel_data': ChannelParser._parse_acc_data(
                    vids_json,
                    errors=errors
                ),
                **ChannelParser._parse_tabs(vids_json, errors=errors),
                'errors': errors if errors else None
            }
        return result


class VideoDataParser:
    @staticmethod
    def _get_likes_and_comments(data) -> dict:
        two_col = data['contents']['twoColumnWatchNextResults']
        two_col_contents = two_col['results']['results']['contents']

        result = {}
        for el in two_col_contents:
            el_text = str(el)
            if 'likeCount' in el_text:
                cut_like = el_text[el_text.find('likeCount') - 1:]
                cut_like = cut_like[:cut_like.find('}') + 1]
                result['likes'] = int(re.findall(r'\d+', cut_like)[0])
            if 'commentCount' in el_text:
                cut_comment = el_text[el_text.find('commentCount') - 1:]
                cut_comment = cut_comment[:cut_comment.find('}') + 1]
                result['comments'] = int(re.findall(r'\d+', cut_comment)[0])
            return result

    @staticmethod
    def get_video_metrics(video_uid: str):
        """
        Collects and returns video statistics, require unique video identifier.
        :param video_uid: unique video identifier
        :return: dict - video_data with video's stats
        """
        resp = requests.get(YT_VIDEO_URL.format(video_uid))
        bs = BeautifulSoup(resp.text, "lxml", parse_only=SoupStrainer('body'))
        scripts = bs.find_all(_filter_vid_details)

        # Store needed data
        video_data = {}
        for scr in scripts:
            inner_text = scr.get_text()
            script_data = json.loads(inner_text[inner_text.find('{') - 1:-1])

            # Collect PlayerResponse data
            if inner_text.startswith('var ytInitialPlayerResponse'):
                vid_details = script_data['videoDetails']
                micro_data = script_data['microformat'][
                    'playerMicroformatRenderer']

                video_data = {
                    **{
                        'channel_id': vid_details['channelId'],
                        'title': vid_details['title'],
                        'length_sec': vid_details['lengthSeconds'],
                        'views': int(vid_details['viewCount']),
                        'pub_date': micro_data['publishDate'],
                        'upl_date': micro_data['uploadDate'],
                        'is_family_safe': micro_data['isFamilySafe'],
                    }, **video_data
                }

            # Collect InitialData
            if inner_text.startswith('var ytInitialData'):
                video_data = {
                    **video_data,
                    **VideoDataParser._get_likes_and_comments(script_data)
                }
        return video_data
