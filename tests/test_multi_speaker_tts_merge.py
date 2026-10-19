import pytest
from pathlib import Path

from oskill._multi_speaker_tts_merge import multi_speaker_tts_merge


def test_empty_raises():
    with pytest.raises(ValueError):
        multi_speaker_tts_merge(audio_paths=[], output_path="/tmp/o.mp3")


def test_fallback_concat(tmp_path):
    a = tmp_path / "a.mp3"
    b = tmp_path / "b.mp3"
    a.write_bytes(b"AAA")
    b.write_bytes(b"BBB")
    out = tmp_path / "out.mp3"
    from unittest.mock import patch
    with patch("shutil.which", return_value=None):
        res = multi_speaker_tts_merge(audio_paths=[a, b], output_path=out)
    assert res == out
    assert out.read_bytes() == b"AAABBB"
