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


# ---------- build_ffmpeg_command ----------
def test_build_ffmpeg_command_basic():
    cmd = main.build_ffmpeg_command("in.mp4", "out.mp4", 28, "libx265", False)
    # Các tham số cốt lõi phải có mặt và đúng thứ tự đầu vào -> đầu ra
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd and cmd[cmd.index("-i") + 1] == "in.mp4"
    assert cmd[cmd.index("-vcodec") + 1] == "libx265"
    assert cmd[cmd.index("-crf") + 1] == "28"
    assert cmd[cmd.index("-acodec") + 1] == "aac"
    # Đường dẫn đầu ra luôn là tham số cuối
    assert cmd[-1] == "out.mp4"


def test_build_ffmpeg_command_crf_is_string():
    cmd = main.build_ffmpeg_command("in.mp4", "out.mp4", 35, "libx264", False)
    # CRF phải được ép về chuỗi cho subprocess
    assert cmd[cmd.index("-crf") + 1] == "35"
    assert cmd[cmd.index("-vcodec") + 1] == "libx264"


def test_build_ffmpeg_command_without_720p_has_no_scale():
    cmd = main.build_ffmpeg_command("in.mp4", "out.mp4", 28, "libx265", False)
    assert "-vf" not in cmd
    assert "scale=-2:720" not in cmd


def test_build_ffmpeg_command_with_720p_adds_scale_filter():
    cmd = main.build_ffmpeg_command("in.mp4", "out.mp4", 28, "libx265", True)
    assert "-vf" in cmd
    assert cmd[cmd.index("-vf") + 1] == "scale=-2:720"
    # Bộ lọc 720p phải đứng trước phần audio/output
    assert cmd.index("-vf") < cmd.index("-acodec")


def test_build_ffmpeg_command_enables_progress_output():
    cmd = main.build_ffmpeg_command("in.mp4", "out.mp4", 28, "libx265", False)
    # Cần -progress pipe:1 để đọc tiến trình realtime
    assert cmd[cmd.index("-progress") + 1] == "pipe:1"
    assert "-nostats" in cmd


# ---------- parse_progress_fraction ----------
def test_parse_progress_fraction_midway():
    # 5 giây trên video 10 giây -> 0.5
    assert main.parse_progress_fraction("out_time_ms=5000000", 10.0) == 0.5


def test_parse_progress_fraction_strips_whitespace():
    assert main.parse_progress_fraction("  out_time_ms=2000000\n", 10.0) == 0.2


def test_parse_progress_fraction_clamped_to_one():
    # Vượt quá độ dài (FFmpeg đôi khi báo dư) -> kẹp về 1.0
    assert main.parse_progress_fraction("out_time_ms=12000000", 10.0) == 1.0


def test_parse_progress_fraction_non_progress_line_returns_none():
    assert main.parse_progress_fraction("frame=123", 10.0) is None
    assert main.parse_progress_fraction("bitrate=N/A", 10.0) is None


def test_parse_progress_fraction_zero_duration_returns_none():
    # Không biết tổng độ dài -> không tính được %
    assert main.parse_progress_fraction("out_time_ms=5000000", 0) is None


def test_parse_progress_fraction_invalid_value_returns_none():
    assert main.parse_progress_fraction("out_time_ms=abc", 10.0) is None


# ---------- make_output_path với output_dir ----------
def test_make_output_path_uses_output_dir():
    path = main.make_output_path(
        os.path.join("videos", "clip.mp4"),
        exists=lambda p: False,
        output_dir=os.path.join("D:", "out"),
    )
    assert path == os.path.join("D:", "out", "clip_da_nen.mp4")


def test_make_output_path_output_dir_with_collision():
    out = os.path.join("D:", "out")
    taken = {os.path.join(out, "clip_da_nen.mp4")}
    path = main.make_output_path(
        os.path.join("videos", "clip.mp4"),
        exists=lambda p: p in taken,
        output_dir=out,
    )
    assert path == os.path.join(out, "clip_da_nen (1).mp4")


def test_make_output_path_none_output_dir_falls_back_to_source():
    path = main.make_output_path(
        os.path.join("videos", "clip.mp4"),
        exists=lambda p: False,
        output_dir=None,
    )
    assert path == os.path.join("videos", "clip_da_nen.mp4")


# ---------- format_size ----------
def test_format_size_bytes():
    assert main.format_size(0) == "0B"
    assert main.format_size(512) == "512B"


def test_format_size_kb_mb_gb():
    assert main.format_size(1536) == "1.5KB"          # 1.5 * 1024
    assert main.format_size(5 * 1024 * 1024) == "5.0MB"
    assert main.format_size(2 * 1024 * 1024 * 1024) == "2.0GB"


def test_format_size_invalid():
    assert main.format_size(None) == "—"
    assert main.format_size(-100) == "—"


# ---------- is_video_file ----------
def test_is_video_file_accepts_known_extensions():
    assert main.is_video_file("a.mp4")
    assert main.is_video_file("B.MKV")        # không phân biệt hoa thường
    assert main.is_video_file(os.path.join("dir", "clip.mov"))


def test_is_video_file_rejects_non_video():
    assert not main.is_video_file("note.txt")
    assert not main.is_video_file("image.png")
    assert not main.is_video_file("noext")


# ---------- parse_dropped_files ----------
def test_parse_dropped_files_simple_splitter():
    # Dùng splitter giả lập kiểu tk.splitlist
    raw = "a.mp4 b.txt c.mkv"
    files = main.parse_dropped_files(raw, splitter=lambda r: r.split())
    assert files == ["a.mp4", "c.mkv"]


def test_parse_dropped_files_handles_braced_paths():
    # Path có khoảng trắng được bọc trong {} (không truyền splitter)
    raw = "{C:/My Videos/clip one.mp4} D:/x.mkv {note.txt}"
    files = main.parse_dropped_files(raw)
    assert files == ["C:/My Videos/clip one.mp4", "D:/x.mkv"]


def test_parse_dropped_files_empty():
    assert main.parse_dropped_files("", splitter=lambda r: []) == []
    assert main.parse_dropped_files("readme.md photo.jpg", splitter=lambda r: r.split()) == []
