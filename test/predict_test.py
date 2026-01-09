
import os
import numpy as np
import threading
import pytest
from types import SimpleNamespace
from source.predict import predict_sono, recording_to_predict
from source import visualise as vis
from source.misc import read_clean_wav

""" Helpers that mimic the YOLO-like objects  """
class DummyBox:
    def __init__(self, xyxy, cls=0, conf=0.85):
        self.xyxy = np.array([xyxy], dtype=float)
        self.cls = np.array([cls])
        self.conf = np.array([conf])

class DummyResult:
    def __init__(self, boxes, orig_shape=(300, 200), names=None): # orig_shape is (height, width)
        self.boxes = boxes
        self.orig_shape = orig_shape
        self.names = names if names is not None else {0: "cat"}

class DummyModel:
    def __init__(self, results):
        self._results = results
        self.to_called = False
    def to(self, device):
        self.to_called = True
    def predict(self, *, source, save, verbose, device, conf, iou):
        return self._results

""" Test conversion bbox to timing and frequency """
def test_predict_sono_basic_calculation():
    # Prepare a single box with coordinates and a result that maps to a class name
    # orig_shape: height=300, width=200
    box = DummyBox(xyxy=[10, 20, 110, 220], cls=0, conf=0.85)
    result = DummyResult(boxes=[box], orig_shape=(300, 200), names={0: "buzz"})
    model = DummyModel(results=[result])

    filenames = ["rec_1000_2000.png"]               # filename stem split[-2] -> "1000"
    wav_path = "/path/to/audio.wav"
    csv_data = predict_sono(model=model, img_array=[np.zeros((10,10,3))], filenames=filenames, wav_path=wav_path, save=False)

    assert isinstance(csv_data, list) and len(csv_data) == 1
    row = csv_data[0]

    # expected calculations:
    # width=200 -> start_time = (10/200)*1000 + 1000 = 50 + 1000 = 1050
    # end_time   = (110/200)*1000 + 1000 = 550 + 1000 = 1550
    assert row["start_time_ms"] == "1050"
    assert row["end_time_ms"] == "1550"
    # frequencies:
    # y_min_corrected = height - y_max = 300 - 220 = 80 -> 80*(120/300)=32
    # y_max_corrected = 300 - 20 = 280 -> 280*(120/300)=112
    assert row["freq_min"] == "32"
    assert row["freq_max"] == "112"
    assert row["category"] == "buzz"
    assert abs(row["confidence"] - 0.85) < 1e-6
    assert row["filename"] == os.path.basename(wav_path)
    assert row["filepath"] == wav_path

""" Test empty return """
def test_predict_sono_no_boxes_returns_empty():
    model = DummyModel(results=[])  # no results
    out = predict_sono(model=model, img_array=[], filenames=[], wav_path="x.wav", save=False)
    assert out == []

""" Test empty array """
def test_predict_sono_save_with_default_dir_raises():
    model = DummyModel(results=[])
    with pytest.raises(ValueError):
        predict_sono(model=model, img_array=[], filenames=[], wav_path="x.wav", save=True)

""" Test recording_to_predict """
def test_recording_to_predict_reads_and_calls_predict(monkeypatch):
    # fake read_clean_wav to return fs and simple audio data
    def fake_read(wav_file):
        fs = 1000
        # 2 seconds of audio -> 2000 samples
        return fs, np.zeros(2000, dtype=np.float32)
    monkeypatch.setattr("source.predict.read_clean_wav", fake_read)

    # fake viz_audio_segment to return image arrays and filename strings
    def fake_viz(segment_data, fs, folder_struc, filename_original, segment_duration, segment_number, time_img, colour_scale, write_plot, magn_weight, draw_freq_lines):
        # return a dummy image array and filename consistent with predict logic
        fname = f"{filename_original}_{time_img[0]}_{time_img[1]}.png"  # stem split[-2] should be the start time
        return np.zeros((10,10,3)), fname
    monkeypatch.setattr("source.visualise.viz_audio_segment", fake_viz)

    # Prepare model that returns a trivial result for each segment
    box = DummyBox(xyxy=[0, 0, 10, 20], cls=0, conf=0.9)
    result = DummyResult(boxes=[box], orig_shape=(100, 100), names={0: "buzz"})
    # model will be used by recording_to_predict -> predict_sono, which will call model.predict once
    model = DummyModel(results=[result])

    out = recording_to_predict(wav_file="/some/file.wav", model=model, output_size=1, overlap=0, write_plot=False)
    # it should return a list with entries corresponding to found boxes (one per segment)
    assert isinstance(out, list)
    assert len(out) >= 1
    # basic sanity on the first row
    first = out[0]
    assert first["category"] == "buzz"
    assert float(first["confidence"]) == 0.9

""" Test cancel event in recording_to_predict when using app """
def test_recording_to_predict_cancel_event(monkeypatch):
    def fake_read(wav_file):
        return 1000, np.zeros(5000)
    monkeypatch.setattr("source.predict.read_clean_wav", fake_read)
    monkeypatch.setattr("source.visualise.viz_audio_segment", lambda *a, **k: (np.zeros((10,10,3)), "x_0_0.png"))

    model = DummyModel(results=[])
    ev = threading.Event()
    ev.set()  # already cancelled
    out = recording_to_predict(wav_file="a.wav", model=model, cancel_event=ev)
    assert out == []  # cancelled immediately
