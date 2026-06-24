# Tài liệu kỹ thuật — Super Video Compressor

Tài liệu này mô tả kiến trúc, luồng hoạt động và chi tiết các thành phần trong mã nguồn,
dành cho lập trình viên muốn hiểu hoặc đóng góp cho dự án. Phần giới thiệu và hướng dẫn
sử dụng cho người dùng cuối nằm ở [README.md](README.md).

## 1. Tổng quan

Super Video Compressor là ứng dụng desktop có giao diện (GUI) dùng để nén video, viết bằng
Python. Lõi xử lý là **FFmpeg**; giao diện dựng bằng **CustomTkinter**. Toàn bộ ứng dụng nằm
trong một file `main.py` duy nhất, kèm file test `test_logic.py`.

| Thành phần | Công nghệ |
|---|---|
| Giao diện | CustomTkinter (Dark mode), đa ngôn ngữ VI/EN |
| Kéo & thả | tkinterdnd2 (tuỳ chọn, tự tắt nếu thiếu) |
| Xử lý video | FFmpeg / ffprobe (qua `static_ffmpeg`) |
| Codec video | H.264/H.265 (CPU: `libx264`/`libx265`; GPU: `h264_nvenc`/`hevc_nvenc`) |
| Codec âm thanh | AAC (chọn bitrate) hoặc copy giữ nguyên |
| Chế độ nén | Theo chất lượng (CRF/CQ) hoặc theo dung lượng mục tiêu (2-pass / ABR) |
| Lưu cấu hình | JSON (`config.json`) |
| Đóng gói | PyInstaller (`SuperVideoCompressor.spec`) |
| Kiểm thử | pytest |
| CI | GitHub Actions |

## 2. Cấu trúc thư mục

```
VideoCompressor/
├── main.py                  # Toàn bộ ứng dụng (logic + GUI)
├── test_logic.py            # Unit test cho các hàm logic thuần
├── requirements.txt         # Phụ thuộc: customtkinter, static_ffmpeg, tkinterdnd2
├── SuperVideoCompressor.spec # Cấu hình build PyInstaller ra .exe
├── README.md                # Giới thiệu & hướng dẫn người dùng
├── DOCS.md                  # Tài liệu kỹ thuật (file này)
├── config.json              # Cấu hình cá nhân (tự sinh, không commit)
├── .gitignore
└── .github/workflows/
    └── tests.yml            # CI chạy pytest trên Python 3.10–3.12
```

## 3. Kiến trúc

Mã nguồn chia làm hai tầng rõ ràng:

### 3.1. Hàm logic thuần (cấp module)

Đây là các hàm không phụ thuộc GUI, nhận tham số rõ ràng và trả về giá trị thuần, nên dễ
kiểm thử độc lập:

| Hàm | Vai trò |
|---|---|
| `make_output_path(input_path, exists, output_dir)` | Sinh đường dẫn file đầu ra, tự thêm hậu tố `(1)`, `(2)`… nếu trùng; hỗ trợ thư mục output riêng. |
| `format_eta(seconds)` | Định dạng số giây còn lại thành `mm:ss` hoặc `h:mm:ss`. |
| `format_size(num_bytes)` / `format_size_change(in, out)` | Định dạng dung lượng dễ đọc; mô tả thay đổi trước/sau kèm cờ cảnh báo khi file phình to. |
| `format_savings(in, out)` | Chuỗi tóm tắt tổng dung lượng tiết kiệm (bản module, không dịch). |
| `is_video_file` / `parse_dropped_files` | Lọc đuôi video; tách chuỗi dữ liệu kéo-thả (hỗ trợ path có dấu cách trong `{}`). |
| `build_ffmpeg_command(...)` | Dựng lệnh FFmpeg một lượt (CRF cho CPU, CQ cho NVENC); nhận `preset`, `ss`/`to`, `audio_bitrate`. |
| `build_two_pass_commands(...)` | Cặp lệnh 2-pass cho chế độ dung lượng mục tiêu (CPU). |
| `build_nvenc_abr_command(...)` | Lệnh NVENC một lượt theo bitrate trung bình (chế độ dung lượng trên GPU). |
| `compute_video_bitrate(target_mb, duration, audio_kbps)` | Tính bitrate video để đạt dung lượng mục tiêu. |
| `parse_progress_fraction(line, duration)` | Đọc dòng `-progress` của FFmpeg thành % (0..1). |
| `is_hardware_encoder` / `nvenc_preset` | Nhận diện encoder phần cứng; ánh xạ preset x264 → p1..p7. |
| `detect_available_encoders` / `_probe_encoder` | Dò encoder GPU **thực sự chạy được** (thử encode 1 frame, tránh dương tính giả). |
| `parse_time_to_seconds` / `trim_args` / `audio_args` | Parse mốc thời gian cắt; dựng tham số cắt và audio cho FFmpeg. |
| `tr(lang, key, **kwargs)` | Tra cứu chuỗi đa ngôn ngữ (fallback về tiếng Việt). |
| `load_config` / `save_config` | Đọc/ghi `config.json` (giữ nguyên Unicode). |

### 3.2. Lớp giao diện `VideoCompressorApp`

Kế thừa `ctk.CTk`. Chịu trách nhiệm dựng giao diện, quản lý trạng thái và điều phối tiến
trình nén. Các method GUI uỷ thác phần logic thuần cho các hàm cấp module ở trên để tránh
trùng lặp và giữ khả năng test.

## 4. Luồng hoạt động chính

```
Mở app
  └─ load_config()  → khôi phục codec, CRF, 720p, thư mục lần trước
  └─ build_ui()     → dựng giao diện
  └─ apply_config() → áp giá trị đã lưu lên widget

Người dùng bấm "Chọn Video"
  └─ select_files() → chọn 1+ file, vẽ danh sách (rebuild_file_list)

Người dùng bấm "BẮT ĐẦU NÉN VIDEO"
  └─ start_compression()
       ├─ validate chế độ dung lượng (MB > 0) và mốc cắt (To > From)
       ├─ save_config()            → nhớ lựa chọn
       ├─ khóa nút, bật nút Hủy, gom opts (mode/codec/preset/audio/trim...)
       └─ Thread → run_batch(files, opts)   → chạy nền, không đơ UI
             └─ với mỗi file:
                  ├─ validate_input_file()  → ffprobe kiểm tra video thật
                  ├─ make_output_path()
                  └─ compress_one()         → điều phối theo chế độ:
                       ├─ CRF: build_ffmpeg_command → _run_ffmpeg (một lượt)
                       └─ Dung lượng: GPU → ABR một lượt; CPU → 2-pass
             └─ tổng kết + savings_text()
       └─ finish_compression()     → khôi phục nút, mở thư mục kết quả

Đổi ngôn ngữ (menu góc trên)
  └─ change_language() → lưu trạng thái → huỷ toàn bộ widget → build_ui() + apply_config()
```

`_run_ffmpeg(command, duration, map_fraction, label)` là helper dùng chung cho mọi lượt
mã hoá: chạy tiến trình, đọc tiến trình realtime và ánh xạ % của lượt hiện tại thành % tổng
của cả lô (nhờ `map_fraction`). Nhờ vậy chế độ một lượt và 2-pass dùng chung một cơ chế.

## 5. Các điểm kỹ thuật quan trọng

### 5.1. Tránh đơ UI

Việc nén nặng nên chạy trong một **thread nền** (`run_batch`). Mọi cập nhật giao diện từ
thread nền đều thực hiện qua `self.after(0, ...)` để đảm bảo an toàn luồng với Tkinter.

### 5.2. Tránh deadlock pipe (quan trọng)

`libx265`/`libx264` ghi rất nhiều ra `stderr`. Nếu chỉ đọc `stdout` (lấy tiến trình) mà
để `stderr` không đọc, buffer `stderr` đầy (~64KB) sẽ làm FFmpeg bị chặn khi ghi tiếp →
ngừng xuất `stdout` → tiến trình đứng hình. `compress_one` xử lý bằng cách **đọc `stderr`
song song trong một thread riêng** (`drain_stderr`), nên buffer không bao giờ đầy.

### 5.3. Theo dõi tiến trình & ETA

FFmpeg chạy với `-progress pipe:1 -nostats`, xuất các dòng `out_time_ms=...`. Kết hợp với
thời lượng video lấy từ `ffprobe` (`get_video_duration`), app tính phần trăm hoàn thành.
ETA suy ra từ thời gian đã trôi qua và phần trăm tổng của cả lô.

### 5.4. An toàn không ghi đè

`make_output_path` luôn tạo tên mới (`_da_nen`, rồi `_da_nen (1)`…) nếu file đích đã tồn
tại, nên không bao giờ ghi đè file có sẵn.

### 5.5. Hủy giữa chừng

`cancel_compression` đặt cờ `is_cancelled` và gọi `process.terminate()`. `run_batch` kiểm
tra cờ này giữa các file để dừng cả lô; file đang nén dở sẽ bị xóa (`_cleanup_partial_output`).

### 5.6. Nén theo dung lượng mục tiêu

`compute_video_bitrate` tính bitrate video từ dung lượng mục tiêu và thời lượng (sau cắt),
trừ phần dành cho audio. Encoder CPU dùng **2-pass** (`build_two_pass_commands`) với file log
tạm trong thư mục temp, được dọn sạch sau mỗi file (kể cả khi lỗi). Encoder GPU dùng **một
lượt ABR** (`build_nvenc_abr_command`) vì NVENC không hỗ trợ 2-pass kiểu log.

### 5.7. Dò GPU an toàn

Một encoder NVENC có thể được biên dịch sẵn trong FFmpeg nhưng vẫn lỗi lúc chạy nếu thiếu
driver (`Cannot load nvcuda.dll`). `detect_available_encoders` vì vậy **thử encode 1 frame**
ra null; chỉ những encoder vượt qua mới được thêm vào danh sách codec, tránh hiển thị lựa
chọn "chết".

### 5.8. Cắt video

Tham số `-ss`/`-to` đặt **sau** `-i` để cắt chính xác theo frame. Khi cắt, thời lượng hiệu
dụng (`To - From`) được dùng cho cả tính % tiến trình lẫn tính bitrate mục tiêu.

### 5.9. Đa ngôn ngữ (i18n)

`TRANSLATIONS` là bảng `{lang: {key: text}}`; `tr()`/`self.t()` tra cứu theo ngôn ngữ hiện
tại. Mã chế độ, codec và trạng thái dùng **token độc lập ngôn ngữ** (vd `"crf"`, `"done"`),
chỉ phần hiển thị mới dịch — nên logic không phụ thuộc ngôn ngữ. Khi đổi ngôn ngữ, app lưu
trạng thái rồi dựng lại toàn bộ giao diện (`change_language`).

## 6. Định dạng `config.json`

```json
{
  "lang": "vi",
  "codec": "libx265",
  "crf": 28,
  "force_720p": false,
  "preset": "fast",
  "mode": "crf",
  "target_mb": "",
  "audio": "128k",
  "trim_enabled": false,
  "trim_from": "",
  "trim_to": "",
  "last_dir": "D:/videos",
  "output_dir": ""
}
```

File này tự sinh cạnh `main.py`, được ghi khi bấm bắt đầu nén và khi đóng app
(`on_close`). Đã thêm vào `.gitignore` vì là cấu hình cá nhân. Lưu ý: `codec` lưu theo
**encoder** (ổn định) còn `mode` lưu theo **token** — nên đổi ngôn ngữ không làm hỏng config.

## 7. Kiểm thử

Test nằm trong `test_logic.py`, chỉ kiểm các hàm logic thuần (không cần GUI), nên chạy
nhanh và ổn định.

```bash
python -m pytest test_logic.py -v
```

Phạm vi: định dạng (`format_eta`, `format_size`, `format_size_change`, `format_savings`),
đường dẫn (`make_output_path`), cấu hình (`load/save_config`), dựng lệnh FFmpeg (CRF, 2-pass,
NVENC ABR — gồm preset, cắt video, audio), tính bitrate mục tiêu (`compute_video_bitrate`),
dò encoder (`detect_available_encoders` với runner giả), parse thời gian/tiến trình, và bảng
dịch i18n — gồm nhiều trường hợp biên.

### Đóng gói `.exe`

```bash
pyinstaller SuperVideoCompressor.spec --noconfirm
```

Spec dùng `collect_all` để gom dữ liệu của `customtkinter`, `tkinterdnd2` (binary tkdnd cho
kéo-thả) và `static_ffmpeg`. Kết quả ở `dist/SuperVideoCompressor.exe`, chạy độc lập.

CI (`.github/workflows/tests.yml`) tự chạy bộ test này trên Python 3.10, 3.11, 3.12 mỗi
khi push hoặc mở PR vào `main`, dùng `xvfb` để chạy được trên môi trường không màn hình.

## 8. Phát triển

```bash
git clone https://github.com/tridpt/VideoCompressor.git
cd VideoCompressor
pip install -r requirements.txt
pip install pytest          # nếu muốn chạy test
python main.py
```

Khi thêm logic mới: ưu tiên viết dưới dạng **hàm thuần cấp module** rồi cho method trong
class gọi lại, để giữ khả năng kiểm thử. Bổ sung test tương ứng trong `test_logic.py`.
