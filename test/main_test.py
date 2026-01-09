import os
import pandas as pd
import builtins
import types
import pytest
import main

from pathlib import Path


""" Helper YOLO object for testing """
class DummyYOLO:
    def __init__(self, model_path):
        self.model_path = model_path

""" Helper: Context manager that mimics ProcessPoolExecutor but runs jobs synchronously """
class DummyExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def map(self, func, iterable):
        # return generator that calls func synchronously for each arg
        return (func(i) for i in iterable)

""" Helper: Returns a fake recording_to_predict function that ignores extra kwargs (partial will add them) """
def make_fake_recording_to_predict(return_per_file):
    if callable(return_per_file):
        def _f(filepath, *args, **kwargs):
            return return_per_file(filepath)
    else:
        def _f(filepath, *args, **kwargs):
            return return_per_file
    return _f

""" Test if correctly handled where no dirs are found in the log file """
def test_no_dirs_found(monkeypatch, capsys):
    monkeypatch.setattr(main, "YOLO", DummyYOLO)
    monkeypatch.setattr(main, "get_dirs_wav", lambda head_dir_list: head_dir_list)
    monkeypatch.setattr(main.log, "logging", lambda path, dirs: [])
    result = main.main(dir_list=["/does/not/matter"], log_path=False, recursive=True, proc=1)

    captured = capsys.readouterr()
    assert "No folders with wav-files found" in captured.out
    assert result is None


""" When dir exists but no wav files are found, main prints and (with app=True) posts msg_queue progress """
def test_no_wav_files_in_dir(monkeypatch, capsys):
    monkeypatch.setattr(main, "YOLO", DummyYOLO)
    monkeypatch.setattr(main, "get_dirs_wav", lambda head_dir_list: ["/fake/dir"])
    monkeypatch.setattr(main.log, "logging", lambda path, dirs: ["/fake/dir"])
    monkeypatch.setattr(main, "glob", types.SimpleNamespace(glob=lambda pattern: []))
    monkeypatch.setattr(main, "time", types.SimpleNamespace(sleep=lambda s: None))

    # msg_queue stub
    class MQ:
        def __init__(self):
            self.msgs = []

        def put(self, msg):
            self.msgs.append(msg)

    mq = MQ()

    # run (app True to exercise message queue calls)
    main.main(dir_list="/fake/dir", log_path=False, msg_queue=mq, app=True, recursive=True, proc=1)

    captured = capsys.readouterr()
    assert "No wav-files found" in captured.out or any("No wav-files found" in str(m) for m in mq.msgs)

""" Tests for storing output and logging """
def test_process_single_dir_writes_output_and_updates_log(tmp_path, monkeypatch):
    proc_dir = tmp_path / "proc_dir"
    proc_dir.mkdir()
    fake_files = [str(proc_dir / "a.WAV"), str(proc_dir / "b.wav")]

    log_path = tmp_path / "logs"
    log_path.mkdir()
    log_csv = log_path / "log.csv"
    pd.DataFrame([{"dir": str(proc_dir), "done": ""}]).to_csv(log_csv, index=False)

    monkeypatch.setattr(main, "YOLO", DummyYOLO)
    monkeypatch.setattr(main, "get_dirs_wav", lambda head_dir_list: [str(proc_dir)])
    monkeypatch.setattr(main.log, "logging", lambda path, dirs: [str(proc_dir)])
    monkeypatch.setattr(main, "glob", types.SimpleNamespace(glob=lambda pattern: fake_files))
    monkeypatch.setattr(main, "ProcessPoolExecutor", DummyExecutor)

    def fake_recording_to_predict(filepath, *args, **kwargs):
        return [{
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "category": "buzz",
            "confidence": 0.9,
            "start_time_ms": 0,
            "end_time_ms": 100,
            "freq_min": 20000,
            "freq_max": 50000
        }]

    monkeypatch.setattr(main, "recording_to_predict", fake_recording_to_predict)
    monkeypatch.setattr(main, "overlap_tidy", lambda df, threshold: df)

    main.main(dir_list=str(proc_dir), log_path=str(log_path), recursive=True, proc=2, files_per_batch=1000)

    expected_output = proc_dir / "output_1-2.csv"
    assert expected_output.exists()
    df_log = pd.read_csv(str(log_csv))
    row = df_log.loc[df_log["dir"] == str(proc_dir)]
    assert not row.empty
    assert row.iloc[0]["done"] == "yes"
