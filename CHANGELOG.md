# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Bilingual UI (Vietnamese / English) with a language switcher; the whole
  interface is rebuilt on switch and the choice is remembered. Internal mode,
  codec, and status identifiers are language-independent.
- Trim before compressing: optional `From`/`To` time range (hh:mm:ss) applied
  to every file; effective duration drives progress and target-bitrate math.
- Audio bitrate control (96k/128k/192k/256k or keep original via stream copy).
- PyInstaller spec (`SuperVideoCompressor.spec`) bundling customtkinter,
  tkinterdnd2, and static_ffmpeg for a standalone `.exe`.
- Pure helpers `parse_time_to_seconds`, `trim_args`, `audio_args`, and `tr`
  (i18n lookup); builders now accept `ss`/`to`/`audio_bitrate`. All unit-tested.
- GPU acceleration via NVIDIA NVENC (`h264_nvenc` / `hevc_nvenc`): GPU codec
  options appear only when a real test-encode succeeds at startup, avoiding
  dead options on machines without the right driver.
- Per-row **✕** button to remove a single file from the list (disabled during
  a running batch).
- Bigger-output warning: a finished file that is not smaller than its source
  is flagged amber with a ⚠ and the grow percentage.
- Pure helpers `is_hardware_encoder`, `nvenc_preset`, `build_nvenc_abr_command`,
  `detect_available_encoders`, and `format_size_change`, all unit-tested.
- Speed preset selector (`ultrafast` … `veryslow`) to trade encoding time for
  compression efficiency; remembered in config (defaults to `fast`).
- Target-size mode: enter a desired MB size per video and the app runs a 2-pass
  encode to hit it, computing the video bitrate from the duration. A mode
  switch toggles between Quality (CRF) and Target Size.
- Pure helpers `compute_video_bitrate` and `build_two_pass_commands`, plus a
  `preset` argument on `build_ffmpeg_command`, all covered by unit tests.
- Drag & drop: drop video files straight onto the list (via `tkinterdnd2`);
  non-video files are filtered out automatically.
- Per-file size report: each row now shows original size, then
  `before ➡️ after (-NN%)` once that file finishes.
- Custom output folder: pick a separate destination folder for compressed
  files (or keep the default "next to source"); the choice is remembered.
- Config now also persists the chosen output folder (the 720p option was
  already remembered).
- Pure helpers `format_size`, `is_video_file`, `parse_dropped_files`, and an
  `output_dir` argument for `make_output_path`, all covered by unit tests.
- Pure helpers `build_ffmpeg_command` and `parse_progress_fraction`, extracted
  from the compression loop, with unit tests covering codec/CRF/720p options
  and progress parsing.
- Technical documentation (`DOCS.md`) covering architecture and internals.
- MIT `LICENSE`, `CONTRIBUTING.md`, and this changelog.
- GitHub Actions CI running the test suite on Python 3.10–3.12.
- Unit tests for pure-logic functions (`test_logic.py`).
- "Bỏ chọn" button to clear the selected file list without deleting files.
- Total size-savings summary shown after a batch finishes.
- Config persistence: remembers codec, CRF, 720p option, and last-used folder.
- Scrollable file list showing per-file status (waiting / compressing / done / failed / skipped).
- Batch compression of multiple files in one run.
- Codec choice between H.265 (`libx265`) and H.264 (`libx264`).
- Estimated time remaining (ETA) next to the progress percentage.
- Cancel button to stop a running compression and clean up partial output.
- Input validation via `ffprobe` before compressing.
- Real-time progress percentage parsed from FFmpeg's `-progress` output.
- Overwrite-safe output naming (`_da_nen`, `_da_nen (1)`, …).
- Full FFmpeg error logging to `video_compressor_error.log`.
- Cross-platform "open output folder" on Windows, macOS, and Linux.

### Fixed
- Added a 30s `timeout` to the `ffprobe` validation and duration calls so a
  hanging/corrupt file can no longer freeze the app.
- Aligned the documented Python version (README now states 3.10+, matching the
  badge and CI matrix).
- Fixed an stderr pipe deadlock that froze compression progress when encoding
  with `libx265`/`libx264` (stderr is now drained on a separate thread).

## [0.1.0]

### Added
- Initial release: single-file GUI video compressor using FFmpeg with H.265,
  AAC audio, adjustable CRF, and an optional 720p downscale.
