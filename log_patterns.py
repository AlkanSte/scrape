from dataclasses import dataclass
from typing import List, Optional
from collections import defaultdict

@dataclass
class LogPattern:
    name: str
    patterns: List[str]
    priority: int
    example: str
    category: str

# Define all known log patterns
REQUEST_PATTERNS = {
    'request_start': LogPattern(
        name='request_start',
        patterns=[
            r'\[34m.*\[39m \| \[36m\[1m     TRACE      \[0m \| axon     \| <-- \| \d+ B \| Videos \|',
            r'Incoming request: UID \d+ - HK .* - timeout .* - stake \d+'
        ],
        priority=1,
        example='[34m2024-06-18 14:29:55.647[0m | [36m[1m     TRACE      [0m | axon     | <-- | 875 B | Videos |',
        category='request_flow'
    ),
    'blacklist_check': LogPattern(
        name='blacklist_check',
        patterns=[
            r'(?:Not )?Blacklisting (?:recognized )?hotkey',
            r'Blacklisted: (?:True|False)(?:, .*)?'
        ],
        priority=2,
        example='Not Blacklisting recognized hotkey 5HK5...',
        category='request_flow'
    ),
    'query_info': LogPattern(
        name='query_info',
        patterns=[
            r'Received scraping request: \d+ videos for query \'.*\'',
            r'Random topic from list: .*',
            r'Parallel requests: \d+ from validator\(s\)'
        ],
        priority=3,
        example='Received scraping request: 8 videos for query \'Cable Management Best Practices\'',
        category='query_processing'
    )
}

VIDEO_SEARCH_PATTERNS = {
    'search_results': LogPattern(
        name='search_results',
        patterns=[
            r'Removed \d+ duplicate search results',
            r'Query .* \+\d+ \| \d+ videos',
            r'Video search took .* s: found \d+ videos'
        ],
        priority=4,
        example='Removed 61 duplicate search results.',
        category='video_search'
    ),
    'video_details': LogPattern(
        name='video_details',
        patterns=[
            r'video_id=\'.*\' title=\'.*\' description=.*length=\d+ views=\d+'
        ],
        priority=5,
        example='video_id=\'bGo5OOTnmvw\' title=\'Example\' description=None length=495 views=95851',
        category='video_search'
    )
}

DOWNLOAD_PATTERNS = {
    'download_start': LogPattern(
        name='download_start',
        patterns=[
            r'Starting concurrent download with \d+ videos',
            r'Downloading \d+ videos with process pool'
        ],
        priority=6,
        example='Starting concurrent download with 12 videos',
        category='download_process'
    ),
    'proxy_usage': LogPattern(
        name='proxy_usage',
        patterns=[
            r'Using proxy: .*:\d+',
            r'Downloaded video .* Proxy used: .* \(\d+\.\d+\)'
        ],
        priority=7,
        example='Using proxy: va2av:WHxvzmjnoK@93.189.230.241:50100',
        category='download_process'
    )
}

ERROR_PATTERNS = {
    'error': LogPattern(
        name='error',
        patterns=[
            r'\[31m\[1m     ERROR      \[0m \|.*',
            r'Error:.*',
            r'Exception:.*'
        ],
        priority=1,
        example='[31m[1m     ERROR      [0m | BlacklistedException: Forbidden',
        category='error_handling'
    )
}

ALL_PATTERNS = {
    **REQUEST_PATTERNS,
    **VIDEO_SEARCH_PATTERNS,
    **DOWNLOAD_PATTERNS,
    **ERROR_PATTERNS
} 