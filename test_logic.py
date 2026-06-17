"""Test cho các hàm logic thuần trong main.py (không cần GUI).

Chạy: python -m pytest test_logic.py -v
"""
import json
import os

import main


# ---------- format_eta ----------
def test_format_eta_seconds_only():
    assert main.format_eta(0) == "00:00"
    assert main.format_eta(5) == "00:05"
    assert main.format_eta(59) == "00:59"


def test_format_eta_minutes():
    assert main.format_eta(60) == "01:00"
    assert main.format_eta(170) == "02:50"   # 2 phút 50 giây
    assert main.format_eta(599) == "09:59"


def test_format_eta_hours():
    assert main.format_eta(3600) == "1:00:00"
    assert main.format_eta(3661) == "1:01:01"


def test_format_eta_negative_clamped_to_zero():
    assert main.format_eta(-10) == "00:00"


def test_format_eta_float_truncated():
    assert main.format_eta(90.9) == "01:30"


# ---------- make_output_path ----------
def test_make_output_path_no_collision():
    # Không file nào tồn tại -> giữ hậu tố _da_nen cơ bản
    path = main.make_output_path(
        os.path.join("videos", "clip.mp4"),
        exists=lambda p: False,
    )
    assert path == os.path.join("videos", "clip_da_nen.mp4")


def test_make_output_path_with_collision():
    # clip_da_nen.mp4 đã tồn tại -> phải nhảy sang (1)
    taken = {os.path.join("videos", "clip_da_nen.mp4")}
    path = main.make_output_path(
        os.path.join("videos", "clip.mp4"),
        exists=lambda p: p in taken,
    )
    assert path == os.path.join("videos", "clip_da_nen (1).mp4")


def test_make_output_path_multiple_collisions():
    taken = {
        os.path.join("v", "a_da_nen.mp4"),
        os.path.join("v", "a_da_nen (1).mp4"),
        os.path.join("v", "a_da_nen (2).mp4"),
    }
    path = main.make_output_path(
        os.path.join("v", "a.mp4"),
        exists=lambda p: p in taken,
    )
    assert path == os.path.join("v", "a_da_nen (3).mp4")


def test_make_output_path_preserves_extension():
    path = main.make_output_path("movie.mkv", exists=lambda p: False)
    assert path == "movie_da_nen.mkv"


# ---------- load_config / save_config ----------
def test_save_then_load_roundtrip(tmp_path):
    cfg_file = str(tmp_path / "config.json")
    data = {"codec": "H.264 (tương thích rộng)", "crf": 30, "force_720p": True, "last_dir": "D:/videos"}
    assert main.save_config(data, cfg_file) is True
    assert main.load_config(cfg_file) == data


def test_load_config_missing_file_returns_empty(tmp_path):
    missing = str(tmp_path / "khong_ton_tai.json")
    assert main.load_config(missing) == {}


def test_load_config_invalid_json_returns_empty(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not valid json ", encoding="utf-8")
    assert main.load_config(str(bad)) == {}


def test_load_config_non_dict_returns_empty(tmp_path):
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    assert main.load_config(str(arr)) == {}


def test_save_config_preserves_unicode(tmp_path):
    cfg_file = str(tmp_path / "c.json")
    data = {"codec": "H.265 (nén sâu)"}
    main.save_config(data, cfg_file)
    raw = (tmp_path / "c.json").read_text(encoding="utf-8")
    # ensure_ascii=False nên tiếng Việt được giữ nguyên, không bị escape \u
    assert "nén sâu" in raw
    assert json.loads(raw) == data


# ---------- format_savings ----------
def test_format_savings_basic():
    # 100MB -> 25MB = tiết kiệm 75%
    mb = 1024 * 1024
    result = main.format_savings(100 * mb, 25 * mb)
    assert "100.0MB" in result
    assert "25.0MB" in result
    assert "75%" in result


def test_format_savings_zero_input_returns_empty():
    assert main.format_savings(0, 0) == ""
    assert main.format_savings(-5, 10) == ""


def test_format_savings_no_reduction():
    mb = 1024 * 1024
    result = main.format_savings(50 * mb, 50 * mb)
    assert "0%" in result


def test_format_savings_larger_output():
    # Trường hợp file sau nén lớn hơn (hiếm) -> % tiết kiệm âm
    mb = 1024 * 1024
    result = main.format_savings(10 * mb, 12 * mb)
    assert "-20%" in result
