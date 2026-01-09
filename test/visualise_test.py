import numpy as np
from source.visualise import spectral_subtraction, create_spectrogram_data, viz_audio_segment, recording_to_visual
import numpy as np
from unittest.mock import patch

@patch("source.visualise.read_clean_wav")
@patch("source.visualise.viz_audio_segment")
def test_recording_to_visual_happy_path(mock_viz, mock_read):
    fs = 48000
    audio = np.random.randn(fs * 2)

    mock_read.return_value = (fs, audio)
    mock_viz.return_value = (np.zeros((400, 1280, 3)), "x.png")

    out = recording_to_visual(
        "fake.wav",
        output_size=1,
        overlap=0,
        write_plot=False
    )

    assert mock_viz.call_count == 2
    assert out is None  # function returns nothing

@patch("source.visualise.read_clean_wav")
def test_recording_to_visual_handles_invalid_wav(mock_read):
    mock_read.return_value = (None, None)

    out = recording_to_visual("bad.wav")

    assert out == []



def test_spectral_subtraction_preserves_length():
    fs = 48000
    x = np.random.randn(fs)
    noise = np.ones(257)

    y = spectral_subtraction(x, noise, fs, magn_weight=0.5)

    # STFT/ISTFT output length is nperseg/2 aligned
    expected_length = len(x)
    hop_length = 512 // 2
    aligned_length = ((expected_length + hop_length - 1) // hop_length) * hop_length

    assert isinstance(y, np.ndarray)
    assert len(y) == aligned_length

def test_spectral_subtraction_zero_weight_is_identityish():
    fs = 44100
    x = np.random.randn(fs)
    noise = np.random.rand(257)

    y = spectral_subtraction(x, noise, fs, magn_weight=0.0)

    # Not bit-identical (STFT/ISTFT), but energy should be close
    assert np.isclose(np.linalg.norm(x), np.linalg.norm(y), rtol=1e-2)

def test_noise_estimation_resampled_if_wrong_length():
    fs = 44100
    x = np.random.randn(fs)
    bad_noise = np.ones(10)  # deliberately wrong

    y = spectral_subtraction(x, bad_noise, fs, magn_weight=1.0)

    hop_length = 512 // 2
    aligned_length = ((len(x) + hop_length - 1) // hop_length) * hop_length

    assert len(y) == aligned_length



def test_spectrogram_shapes_and_bounds():
    fs = 48000
    dur = 1.0
    x = np.random.randn(int(fs * dur))

    f, t, Sxx = create_spectrogram_data(
        segment_data=x,
        fs=fs,
        magn_weight=0,
        segment_duration=dur
    )

    assert f.ndim == 1
    assert t.ndim == 1
    assert Sxx.shape == (len(f), len(t))
    assert np.all(Sxx >= 0)

def test_frequency_padding_up_to_120khz():
    fs = 96000  # Nyquist < 120k
    x = np.random.randn(fs)

    f, _, Sxx = create_spectrogram_data(x, fs, 0, 1.0)

    assert f[-1] >= 120_000
    assert Sxx.shape[0] == len(f)

def test_time_padding_to_segment_duration():
    fs = 48000
    x = np.random.randn(int(0.5 * fs))

    _, t, _ = create_spectrogram_data(x, fs, 0, segment_duration=1.0)

    assert t[-1] >= 1.0 - 1e-2 # give a bit of tolerance



def test_viz_returns_image_and_filename(tmp_path):
    fs = 48000
    x = np.random.randn(fs)

    img, fname = viz_audio_segment(
        segment_data=x,
        fs=fs,
        folder_struc=str(tmp_path),
        filename_original="testfile",
        segment_duration=1,
        segment_number=1,
        time_img=[0, 1000],
        colour_scale="jet",
        write_plot=False,
        magn_weight=0,
        draw_freq_lines=True
    )

    assert img.shape[:2] == (400, 1280)
    assert img.ndim == 3
    assert fname.startswith("IMG_testfile")

def test_freq_lines_draw_white_rows():
    fs = 48000
    x = np.random.randn(fs)

    img, _ = viz_audio_segment(
        x, fs, ".", "f", 1, 1, [0, 1000],
        "jet", False, 0, True
    )

    # white rows exist
    assert np.any(img[:, :, 0] == 255)


