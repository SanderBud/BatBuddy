
import os
import pandas as pd
import pytest
from pathlib import Path

from source.log import read_log_file, log_file_correctness_check, logging

""" Tests on reading df """
def test_read_log_file_success(tmp_path):
    p = tmp_path / "log.csv"
    p.write_text("dir,done\n/a,yes\n/b,no\n")
    df = read_log_file(str(p))
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["dir", "done"]
    assert df.shape == (2, 2)

def test_read_log_file_empty(tmp_path, capsys):
    p = tmp_path / "empty.csv"
    p.write_text("")  # empty file
    df = read_log_file(str(p))
    captured = capsys.readouterr()
    assert df is None
    assert "is empty" in captured.out

def test_read_log_file_parser_error(monkeypatch, capsys):
    # Force pandas.read_csv to raise ParserError to hit that except branch
    def fake_read_csv(path):
        raise pd.errors.ParserError("parse fail")
    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    df = read_log_file("some/path.csv")
    out = capsys.readouterr().out
    assert df is None
    assert "could not be parsed" in out

""" Tests on correctness layout log csv """
def test_log_file_correctness_check_valid():
    df = pd.DataFrame({"dir": ["/a", "/b"], "done": ["yes", "no"]})
    # Should not raise
    assert log_file_correctness_check(df) is None

@pytest.mark.parametrize("bad_df", [None, pd.DataFrame()])
def test_log_file_correctness_check_none_or_empty(bad_df):
    with pytest.raises(ValueError):
        log_file_correctness_check(bad_df)

def test_log_file_correctness_check_wrong_column_count():
    df = pd.DataFrame({"a": [1,2], "b": [3,4], "c": [5,6]})
    with pytest.raises(SystemExit):
        log_file_correctness_check(df)

def test_log_file_correctness_check_wrong_column_names():
    df = pd.DataFrame({"wrong": ["/a"], "also_wrong": ["no"]})
    with pytest.raises(SystemExit):
        log_file_correctness_check(df)

def test_log_file_correctness_check_invalid_done_values():
    df = pd.DataFrame({"dir": ["/a"], "done": ["maybe"]})
    with pytest.raises(SystemExit):
        log_file_correctness_check(df)

""" Tests workings of parameters in logging function """
def test_logging_no_logging_requested():
    dirs = ["/a", "/b"]
    out = logging(False, dirs)
    assert out == dirs

def test_logging_create_log_file(tmp_path, capsys):
    path = tmp_path
    dirs = ["/a", "/b"]
    # ensure no log.csv exists
    log_path = path / "log.csv"
    if log_path.exists():
        log_path.unlink()
    out = logging(str(path), dirs)
    captured = capsys.readouterr().out
    assert out == dirs
    assert log_path.exists()
    df = pd.read_csv(log_path)
    assert list(df.columns) == ["dir", "done"]
    assert (df["done"] == "no").all()
    assert "Initialising log file" in captured

""" Checks if existence of log file is handled correctly """
def test_logging_existing_log_continue(tmp_path, capsys):
    path = tmp_path
    dirs = ["a", "b", "c"] # choose dirs in alphabetical order so sorting in function won't change order
    log_path = path / "log.csv"
    pd.DataFrame({"dir": dirs, "done": ["yes", "no", "no"]}).to_csv(log_path, index=False) # create an existing log file with one 'yes' and two 'no'

    remaining = logging(str(path), dirs)
    captured = capsys.readouterr().out # remaining should be list of dirs with done == "no" from the file (sorted by dir in function)
    
    assert isinstance(remaining, list)
    assert set(remaining) == {"b", "c"}
    assert "Continue analysis where we left off" in captured

""" Checks if an instance where all dirs are already analysed is handled correctly """
def test_logging_existing_log_all_done_raises_systemexit(tmp_path):
    path = tmp_path
    dirs = ["a", "b"]
    log_path = path / "log.csv"
    pd.DataFrame({"dir": dirs, "done": ["yes", "yes"]}).to_csv(log_path, index=False)
    with pytest.raises(SystemExit):
        logging(str(path), dirs)

""" Checks if an instance where the requested folders does not match the folders in the log file is handled correctly """
def test_logging_existing_log_mismatch_raises_systemexit(tmp_path, capsys):
    path = tmp_path
    dirs = ["a", "b", "c"]
    log_path = path / "log.csv"
    pd.DataFrame({"dir": ["x", "y"], "done": ["no", "no"]}).to_csv(log_path, index=False)
    with pytest.raises(SystemExit):
        logging(str(path), dirs)

