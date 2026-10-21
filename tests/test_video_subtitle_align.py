from oskill._video_subtitle_align import video_subtitle_align


def test_basic():
    subs = [{"start": 0, "end": 2, "text": "hi"}, {"start": 2, "end": 1, "text": "x"}]
    res = video_subtitle_align(subtitles=subs, audio_duration=5.0)
    assert res[0]["end"] == 2
    assert res[1]["end"] == 3  # clamped/fixed


def test_wrap():
    subs = [{"start": 0, "end": 1, "text": "a " * 30}]
    res = video_subtitle_align(subtitles=subs, max_chars_per_line=10)
    assert "\n" in res[0]["text"]
