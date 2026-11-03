"""Tests for the web app. yt-dlp is replaced by fakes, so nothing talks to YouTube."""

import html

import pytest
from yt_dlp.utils import DownloadError

import main

# Shaped like a real googlevideo.com link: the query string carries the expiry,
# the viewer's IP (a documentation address here) and the signature.
FAKE_LINK = 'https://rr1---sn-test.googlevideo.com/videoplayback?expire=1&ip=203.0.113.7&itag=18&sig=abc'
FAKE_VIDEO = {'url': FAKE_LINK, 'title': 'Demo video', 'ext': 'mp4'}


@pytest.fixture
def client():
    main.app.config.update(TESTING=True)
    return main.app.test_client()


@pytest.fixture
def fake_get_video(monkeypatch):
    """Replace get_video. Set .result or .error, read .calls afterwards."""

    class Fake:
        result = FAKE_VIDEO
        error = None
        calls = []

        def __call__(self, youtube_video_id):
            self.calls.append(youtube_video_id)
            if self.error:
                raise self.error
            return self.result

    fake = Fake()
    fake.calls = []
    monkeypatch.setattr(main, 'get_video', fake)
    return fake


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL and remembers how it was called."""

    info = {'url': FAKE_LINK, 'title': 'Demo video', 'ext': 'mp4'}
    seen = {}

    def __init__(self, options):
        FakeYoutubeDL.seen['options'] = options

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, youtube_video_id, download):
        FakeYoutubeDL.seen['args'] = (youtube_video_id, download)
        return FakeYoutubeDL.info


@pytest.mark.parametrize('path', ['/', '/?v=', '/?v=%20%20'])
def test_home_without_a_video_shows_the_form(client, fake_get_video, path):
    response = client.get(path)

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'name="v"' in page
    assert '<video' not in page
    assert fake_get_video.calls == []


def test_v_plays_the_direct_link(client, fake_get_video):
    response = client.get('/?v=JJo-zUi9E5U')

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert fake_get_video.calls == ['JJo-zUi9E5U']
    assert f'<source src="{html.escape(FAKE_LINK)}" type="video/mp4">' in page
    assert 'Demo video' in page
    assert 'video.min.js' in page


def test_page_shows_the_link_without_its_query_string(client, fake_get_video):
    page = client.get('/?v=JJo-zUi9E5U').get_data(as_text=True)

    # The full link is the href, but the visible text stops before the query
    # string, which holds the viewer's IP and the signature.
    assert f'href="{html.escape(FAKE_LINK)}"' in page
    assert '>https://rr1---sn-test.googlevideo.com/videoplayback?…</a>' in page


def test_a_full_youtube_link_is_passed_to_yt_dlp_as_is(client, fake_get_video):
    link = 'https://www.youtube.com/watch?v=JJo-zUi9E5U&list=PL123'

    response = client.get('/', query_string={'v': link})

    assert response.status_code == 200
    assert fake_get_video.calls == [link]


def test_the_player_uses_the_format_yt_dlp_reports(client, fake_get_video):
    fake_get_video.result = {**FAKE_VIDEO, 'ext': 'webm'}

    page = client.get('/?v=abc').get_data(as_text=True)

    assert 'type="video/webm"' in page


def test_the_title_is_escaped(client, fake_get_video):
    fake_get_video.result = {**FAKE_VIDEO, 'title': '<script>alert(1)</script>'}

    page = client.get('/?v=abc').get_data(as_text=True)

    assert '<script>alert(1)</script>' not in page
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page


def test_when_yt_dlp_fails_the_page_says_why(client, fake_get_video):
    fake_get_video.error = DownloadError('ERROR: [youtube] xxxxxxxxxxx: This video is unavailable')

    response = client.get('/?v=xxxxxxxxxxx')

    assert response.status_code == 502
    page = response.get_data(as_text=True)
    assert 'This video is unavailable' in page
    assert '<video' not in page


def test_get_video_asks_yt_dlp_for_one_pre_merged_file(monkeypatch):
    monkeypatch.setattr(main, 'YoutubeDL', FakeYoutubeDL)

    assert main.get_video('JJo-zUi9E5U') == FAKE_VIDEO
    assert FakeYoutubeDL.seen['args'] == ('JJo-zUi9E5U', False)
    options = FakeYoutubeDL.seen['options']
    assert options['format'] == 'best'
    assert options['noplaylist'] is True
    assert options['skip_download'] is True


def test_get_video_fills_in_missing_title_and_ext(monkeypatch):
    monkeypatch.setattr(main, 'YoutubeDL', FakeYoutubeDL)
    monkeypatch.setattr(FakeYoutubeDL, 'info', {'url': FAKE_LINK})

    assert main.get_video('abc') == {'url': FAKE_LINK, 'title': 'abc', 'ext': 'mp4'}


def test_get_video_without_a_link_raises_download_error(monkeypatch):
    # e.g. a playlist page: yt-dlp returns entries, not one file.
    monkeypatch.setattr(main, 'YoutubeDL', FakeYoutubeDL)
    monkeypatch.setattr(FakeYoutubeDL, 'info', {'title': 'A playlist', 'entries': []})

    with pytest.raises(DownloadError):
        main.get_video('PL123')
