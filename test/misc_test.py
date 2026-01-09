import os
import numpy as np
import pytest
from scipy.io.wavfile import write
import os
import source.misc

""" read_clean_wav tests """ 
def make_wav(path, fs=192000, duration=0.01):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    sig = (0.5 * np.sin(2 * np.pi * 20000 * t)).astype(np.float32)
    write(path, fs, sig)

def test_read_valid_wav(tmp_path):
    wav = tmp_path / "test.wav"
    make_wav(wav)

    fs, audio = read_clean_wav(wav)

    assert fs == 192000
    assert audio is not None
    assert audio.ndim == 1
    assert np.isclose(np.max(np.abs(audio)), 1.0)

def test_empty_wav_logs_and_returns_none(tmp_path):
    wav = tmp_path / "empty.wav"
    write(wav, 192000, np.array([], dtype=np.float32))

    fs, audio = read_clean_wav(wav)

    assert fs is None
    assert audio is None
    log = tmp_path / "corrupted_files_log.txt"
    assert log.exists()
    assert "File does not contain audio data" in log.read_text()

def test_nonexistent_file_logs_error(tmp_path):
    fake = tmp_path / "nope.wav"

    fs, audio = read_clean_wav(fake)

    assert fs is None
    assert audio is None
    log = tmp_path / "corrupted_files_log.txt"
    assert log.exists()
    assert "No such file" in log.read_text() or "cannot find" in log.read_text().lower()

def test_highpass_removes_low_freq(tmp_path):
    fs = 192000
    t = np.linspace(0, 0.01, int(fs * 0.01), endpoint=False)
    low = np.sin(2 * np.pi * 1000 * t)      # should be attenuated
    high = np.sin(2 * np.pi * 30000 * t)    # should survive
    sig = (low + high).astype(np.float32)

    wav = tmp_path / "mix.wav"
    write(wav, fs, sig)

    _, audio = read_clean_wav(wav)

    assert np.std(audio) > 0

""" get_dirs_wav tests """
def test_single_dir_with_wav(tmp_path):
    d = tmp_path / "a"
    d.mkdir()
    (d / "x.wav").touch()
    (d / "y.txt").touch()

    out = get_dirs_wav(d)

    assert out == [str(d)]

def test_nested_dirs(tmp_path):
    d1 = tmp_path / "a"
    d2 = d1 / "b"
    d2.mkdir(parents=True)
    (d2 / "x.WAV").touch()

    out = get_dirs_wav(tmp_path)

    assert str(d2) in out
    assert len(out) == 1

def test_multiple_heads(tmp_path):
    d1 = tmp_path / "a"
    d2 = tmp_path / "b"
    d1.mkdir(); d2.mkdir()
    (d1 / "x.wav").touch()
    (d2 / "y.wav").touch()

    out = get_dirs_wav([d1, d2])

    assert set(out) == {str(d1), str(d2)}

def test_no_wavs(tmp_path):
    d = tmp_path / "a"
    d.mkdir()
    (d / "x.txt").touch()

    out = get_dirs_wav(d)

    assert out == []
