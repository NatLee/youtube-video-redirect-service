"""YouTube Video Redirector: get the direct file link of a YouTube video and play it.

Open ``/?v=<video id or YouTube link>``. yt-dlp looks up the video, the page shows
the direct link it found and plays that link in the browser.
"""

import os

from flask import Flask, render_template, request
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# What we ask yt-dlp for. "best" is the best format that already has video and
# sound in one file, so a plain <video> tag can play it. "noplaylist" keeps a
# watch link that also carries &list=... to that one video.
YDL_OPTIONS = {
    'quiet': True,
    'forceurl': True,
    'skip_download': True,
    'noplaylist': True,
    'format': 'best',
}

app = Flask(__name__)


def get_video(youtube_video_id):
    """Ask yt-dlp for a video's direct link, title and file extension."""
    with YoutubeDL(YDL_OPTIONS) as yd:
        info = yd.extract_info(youtube_video_id, download=False)

    video_url = info.get('url')
    if not video_url:
        raise DownloadError(f'yt-dlp found no single playable file for {youtube_video_id!r}')

    return {
        'url': video_url,
        'title': info.get('title') or youtube_video_id,
        'ext': info.get('ext') or 'mp4',
    }


@app.route('/')
def index():
    youtube_video_id = request.args.get('v', '').strip()
    if not youtube_video_id:
        return render_template('index.html')

    try:
        video = get_video(youtube_video_id)
    except DownloadError as error:
        # Wrong ID, a private video, or YouTube refused: show yt-dlp's reason.
        return render_template('index.html', video_id=youtube_video_id, error=str(error)), 502

    return render_template('index.html', video_id=youtube_video_id, video=video)


if __name__ == '__main__':
    # Development server with the same defaults as always (the Docker image runs
    # gunicorn instead). HOST and PORT override them, e.g. when 5000 is taken.
    app.run(
        host=os.environ.get('HOST', '0.0.0.0'),
        port=int(os.environ.get('PORT', '5000')),
        debug=True,
    )
