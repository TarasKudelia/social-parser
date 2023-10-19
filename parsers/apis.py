import json
import requests


class YouTubeAPI:
    """
    All requests to the YouTubeAPI cost "quota" points (QP).
    Every day user gets 10_000 QPs, different requests costs different amount.

    NOTE: This amount can be changed by Google, but for simplicity:
      - Retrieves a list of resources (channels, videos, playlists) ~ 1 QP.
      - Write operation that creates, updates, or deletes a resource ~ 50 QP.
      - Search request = 100 QP.
      - Video upload = 1_600 QP.
    """

    YT_API_BASE_URL = 'https://www.googleapis.com/youtube/v3'
    YT_SEARCH_URL = f'{YT_API_BASE_URL}/search'
    YT_GET_VIDS_URL = f'{YT_API_BASE_URL}/videos'

    def __init__(self, api_key):
        self.api_key = api_key

    def _search_channel_by_name(self, channel_name: str, max_results: int = 1):
        """ Searches for a YT channel by username. """
        q_params = {
            'q': channel_name,
            'maxResults': max_results,
            'key': self.api_key,
            'part': 'snippet',
            'type': 'channel',
            'order': 'relevance',
            'safeSearch': 'none',
        }
        json_url = requests.get(YouTubeAPI.YT_SEARCH_URL, params=q_params)
        data = json.loads(json_url.text)
        return data

    def _get_videos_by_channel_uid(self, channel_uid: str, from_date, to_date):
        q_params = {
            'key': self.api_key,
        }
        json_url = requests.get(YouTubeAPI.YT_GET_VIDS_URL, params=q_params)
        data = json.loads(json_url.text)
        return data