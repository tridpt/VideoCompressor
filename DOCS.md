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
| Giao diện | CustomTkinter (Dark mode) |
| Xử lý video | FFmpeg / ffprobe (qua `static_ffmpeg`) |
| Codec video | H.265 (`libx265`) hoặc H.264 (`libx264`) |
| Codec âm thanh | AAC |
| Lưu cấu hình | JSON (`config.json`) |
| Kiểm thử | pytest |
| CI | GitHub Actions |

## 2. Cấu trúc thư mục

```
VideoCompressor/
├── main.py                  # Toàn bộ ứng dụng (logic + GUI)
├── test_logic.py            # Unit test cho các hàm logic thuần
├── requirements.txt         # Phụ thuộc: customtkinter, static_ffmpeg
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
| `make_output_path(input_path, exists)` | Sinh đường dẫn file đầu ra, tự thêm hậu tố `(1)`, `(2)`… nếu trùng. Tham số `exists` cho phép thay hàm kiểm tra tồn tại khi test. |
| `format_eta(seconds)` | Định dạng số giây còn lại thành `mm:ss` hoặc `h:mm:ss`. |
| `format_savings(in_bytes, out_bytes)` | Tạo chuỗi tóm tắt tổng dung lượng trước/sau và % tiết kiệm. |
| `load_config(path)` | Đọc `config.json`, trả về dict rỗng nếu thiếu/hỏng. |
| `save_config(data, path)` | Ghi dict cấu hình ra JSON (giữ nguyên Unicode). |

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
       ├─ save_config()            → nhớ lựa chọn
       ├─ khóa nút, bật nút Hủy
       └─ Thread → run_batch()     → chạy nền, không đơ UI
             └─ với mỗi file:
                  ├─ validate_input_file()  → ffprobe kiểm tra video thật
                  ├─ make_output_path()
                  └─ compress_one()         → gọi FFmpeg, đọc tiến trình
             └─ tổng kết + format_savings()
       └─ finish_compression()     → khôi phục nút, mở thư mục kết quả
```

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

## 6. Định dạng `config.json`

```json
{
  "codec": "H.265 (nén sâu)",
  "crf": 28,
  "force_720p": false,
  "last_dir": "D:/videos"
}
```

File này tự sinh cạnh `main.py`, được ghi khi bấm bắt đầu nén và khi đóng app
(`on_close`). Đã thêm vào `.gitignore` vì là cấu hình cá nhân.

## 7. Kiểm thử

Test nằm trong `test_logic.py`, chỉ kiểm các hàm logic thuần (không cần GUI), nên chạy
nhanh và ổn định.

```bash
python -m pytest test_logic.py -v
```

Phạm vi: `format_eta`, `make_output_path`, `format_savings`, `load_config`, `save_config`
— gồm các trường hợp biên (số âm, trùng nhiều lần, JSON hỏng, input bằng 0…).

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
