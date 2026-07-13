"""共享作品详情样例。"""

from __future__ import annotations

from typing import Any

VIDEO_DETAIL: dict[str, Any] = {
    'aweme_id': '1234567890',
    'video': {
        'bit_rate': [
            {
                'bit_rate': 1000,
                'is_h265': 0,
                'is_bytevc1': 0,
                'play_addr': {
                    'width': 720,
                    'height': 1280,
                    'data_size': 1000,
                    'url_list': ['https://example.com/h264-720.mp4'],
                },
            },
            {
                'bit_rate': 2000,
                'is_h265': 0,
                'is_bytevc1': 0,
                'play_addr': {
                    'width': 1080,
                    'height': 1920,
                    'data_size': 3000,
                    'url_list': ['https://example.com/h264-1080.mp4'],
                },
            },
            {
                'bit_rate': 1800,
                'is_h265': 1,
                'is_bytevc1': 1,
                'play_addr': {
                    'width': 1080,
                    'height': 1920,
                    'data_size': 2500,
                    'url_list': ['https://example.com/h265-1080.mp4'],
                },
            },
            {
                'bit_rate': 1500,
                'is_h265': 1,
                'is_bytevc1': 1,
                'play_addr': {
                    'width': 720,
                    'height': 1280,
                    'data_size': 1500,
                    'url_list': ['https://example.com/h265-720.mp4'],
                },
            },
        ],
        'play_addr': {'url_list': ['https://example.com/fallback.mp4']},
    },
}

IMAGE_DETAIL: dict[str, Any] = {
    'aweme_id': '111',
    'aweme_type': 68,
    'images': [
        {
            'uri': 'img0',
            'url_list': [
                'https://example.com/a.webp',
                'https://example.com/a.jpeg',
            ],
            'width': 1080,
            'height': 1920,
        },
        {
            'uri': 'img1',
            'url_list': ['https://example.com/b.webp'],
            'width': 1080,
            'height': 1920,
        },
    ],
}

LIVE_DETAIL: dict[str, Any] = {
    'aweme_id': '222',
    'aweme_type': 68,
    'images': [
        {
            'uri': 'live0',
            'clip_type': 5,
            'url_list': ['https://example.com/live0.jpeg'],
            'video': {
                'play_addr': {'url_list': ['https://example.com/live0.mp4']},
                'bit_rate': [
                    {
                        'is_h265': 0,
                        'play_addr': {
                            'data_size': 100,
                            'url_list': ['https://example.com/live0-small.mp4'],
                        },
                    },
                    {
                        'is_h265': 0,
                        'play_addr': {
                            'data_size': 500,
                            'url_list': ['https://example.com/live0-large.mp4'],
                        },
                    },
                ],
            },
        },
        {
            'uri': 'live1',
            'clip_type': 5,
            'url_list': ['https://example.com/live1.jpeg'],
            'video': {
                'bit_rate': [
                    {
                        'is_h265': 1,
                        'is_bytevc1': 1,
                        'play_addr': {
                            'data_size': 200,
                            'url_list': ['https://example.com/live1-h265.mp4'],
                        },
                    },
                    {
                        'is_h265': 0,
                        'play_addr': {
                            'data_size': 800,
                            'url_list': ['https://example.com/live1-h264-big.mp4'],
                        },
                    },
                ],
            },
        },
    ],
}
