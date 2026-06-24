import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import json
import time
import glob
import tempfile
import subprocess
import threading
import static_ffmpeg

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    _DND_AVAILABLE = False

# Tạo biến môi trường chứa ffmpeg (Nếu máy chưa cài ffmpeg thì cái này tự xử lý)
static_ffmpeg.add_paths()

# Cài đặt giao diện chung
ctk.set_appearance_mode("Dark")  # Giao diện Dark mode xịn xò
ctk.set_default_color_theme("blue")  # Màu chủ đạo là xanh dương

# Bản đồ codec CPU: khoá nhãn (để dịch) -> tham số FFmpeg
CODECS = {
    "codec_h265": "libx265",
    "codec_h264": "libx264",
}

# Codec tăng tốc GPU NVIDIA (chỉ thêm vào lựa chọn nếu máy hỗ trợ)
GPU_CODECS = {
    "codec_h265_gpu": "hevc_nvenc",
    "codec_h264_gpu": "h264_nvenc",
}

# Nơi lưu cấu hình (cạnh file script để dễ tìm)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Mã trạng thái nội bộ (độc lập ngôn ngữ) -> màu hiển thị
STATUS_WAITING = "waiting"
STATUS_COMPRESSING = "compressing"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

STATUS_COLORS = {
    STATUS_WAITING: "gray",
    STATUS_COMPRESSING: "orange",
    STATUS_DONE: "#3ba55d",
    STATUS_FAILED: "#e02f2f",
    STATUS_SKIPPED: "#e0a82f",
}

# Đuôi file video được chấp nhận (dùng cho cả dialog lẫn kéo-thả)
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v"}

# Các preset tốc độ của x264/x265 (nhanh -> chậm, chậm hơn = nén tốt hơn)
PRESETS = [
    "ultrafast", "superfast", "veryfast", "faster",
    "fast", "medium", "slow", "slower", "veryslow",
]

# Mã chế độ nén nội bộ (độc lập ngôn ngữ)
MODE_CRF = "crf"
MODE_SIZE = "size"

# Lựa chọn bitrate audio (giá trị gửi cho FFmpeg, "copy" = giữ nguyên)
AUDIO_BITRATES = ["96k", "128k", "192k", "256k", "copy"]

# Ngôn ngữ hỗ trợ
LANGUAGES = ["vi", "en"]

# Bảng dịch giao diện. Khoá độc lập ngôn ngữ; giá trị theo từng ngôn ngữ.
TRANSLATIONS = {
    "vi": {
        "title": "Super Video Compressor",
        "header": "⚡ NÉN VIDEO SIÊU TỐC ⚡",
        "subtitle": "Giảm đến 90% dung lượng mà không nhận ra sự khác biệt!",
        "lang_label": "Ngôn ngữ:",
        "file_none": "Chưa chọn video nào...",
        "file_many": "Đã chọn {n} video",
        "btn_select": "Chọn Video",
        "btn_clear": "Bỏ chọn",
        "list_label": "Danh sách video",
        "list_label_dnd": "Danh sách video — kéo & thả file vào đây",
        "lbl_codec": "Codec:",
        "codec_h265": "H.265 (nén sâu)",
        "codec_h264": "H.264 (tương thích rộng)",
        "codec_h265_gpu": "H.265 GPU (NVIDIA)",
        "codec_h264_gpu": "H.264 GPU (NVIDIA)",
        "lbl_preset": "Tốc độ (preset):",
        "preset_hint": "← nhanh hơn | nén tốt hơn →",
        "lbl_mode": "Chế độ:",
        "mode_crf": "Chất lượng (CRF)",
        "mode_size": "Dung lượng mục tiêu (MB)",
        "lbl_target": "Dung lượng mục tiêu mỗi video:",
        "target_unit": "MB (nén 2-pass)",
        "lbl_quality": "Mức nén (CRF):",
        "crf_big": "{v} (Dung lượng lớn)",
        "crf_rec": "{v} (Khuyên dùng)",
        "crf_strong": "{v} (Ép nén mạnh)",
        "check_720p": "Ép video về chất lượng HD 720p (Đảm bảo dung lượng sẽ giảm cực sâu)",
        "lbl_trim": "Cắt video (tuỳ chọn):",
        "trim_from": "Từ",
        "trim_to": "Đến",
        "trim_ph": "hh:mm:ss",
        "lbl_audio": "Âm thanh:",
        "audio_copy": "Giữ nguyên",
        "output_to": "Lưu vào:",
        "output_default": "Cạnh file gốc (mặc định)",
        "btn_reset_output": "Mặc định",
        "btn_choose_output": "Chọn thư mục",
        "lbl_progress": "Tiến trình nén:",
        "btn_start": "🚀 BẮT ĐẦU NÉN VIDEO",
        "btn_start_running": "Đang xử lý, vui lòng chờ...",
        "btn_cancel": "✖ HỦY",
        "btn_cancel_running": "Đang hủy...",
        "status_waiting": "chờ",
        "status_compressing": "đang nén",
        "status_done": "xong",
        "status_failed": "lỗi",
        "status_skipped": "bỏ qua",
        "warn_no_files": "Vui lòng chọn video trước khi nén!",
        "warn_bad_target": "Vui lòng nhập dung lượng mục tiêu hợp lệ (số MB > 0).",
        "warn_bad_trim": "Mốc thời gian cắt không hợp lệ. Dùng dạng hh:mm:ss và 'Đến' phải lớn hơn 'Từ'.",
        "warn_dialog_title": "Cảnh báo",
        "drop_invalid": "Không tìm thấy file video hợp lệ trong nội dung vừa thả.",
        "preparing": "Đang chuẩn bị...",
        "compressing": "Đang nén...",
        "compressing_gpu": "Đang nén (GPU)...",
        "pass1": "Lượt 1/2 (phân tích)...",
        "pass2": "Lượt 2/2 (mã hoá)...",
        "file_done": "Hoàn tất file...",
        "cancelled": "⏹ Đã hủy nén video.",
        "done_all": "✅ XONG! Đã nén {ok}/{total} video. {savings}",
        "partial": "⚠ Hoàn tất: {ok}/{total} video thành công, phần còn lại bị lỗi (xem log). {savings}",
        "none_done": "❌ Không nén được video nào (xem log).",
        "sys_error": "❌ Lỗi do hệ thống: {err}",
        "savings": "Tổng: {in_mb:.1f}MB ➡️ {out_mb:.1f}MB (tiết kiệm {pct:.0f}%)",
        "eta": " • Còn lại ~{eta}",
    },
    "en": {
        "title": "Super Video Compressor",
        "header": "⚡ SUPER VIDEO COMPRESSOR ⚡",
        "subtitle": "Shrink files by up to 90% with no visible quality loss!",
        "lang_label": "Language:",
        "file_none": "No video selected yet...",
        "file_many": "{n} videos selected",
        "btn_select": "Select Videos",
        "btn_clear": "Clear",
        "list_label": "Video list",
        "list_label_dnd": "Video list — drag & drop files here",
        "lbl_codec": "Codec:",
        "codec_h265": "H.265 (smallest)",
        "codec_h264": "H.264 (most compatible)",
        "codec_h265_gpu": "H.265 GPU (NVIDIA)",
        "codec_h264_gpu": "H.264 GPU (NVIDIA)",
        "lbl_preset": "Speed (preset):",
        "preset_hint": "← faster | smaller →",
        "lbl_mode": "Mode:",
        "mode_crf": "Quality (CRF)",
        "mode_size": "Target size (MB)",
        "lbl_target": "Target size per video:",
        "target_unit": "MB (2-pass)",
        "lbl_quality": "Compression (CRF):",
        "crf_big": "{v} (large file)",
        "crf_rec": "{v} (recommended)",
        "crf_strong": "{v} (strong compression)",
        "check_720p": "Force HD 720p (guarantees a much smaller file)",
        "lbl_trim": "Trim video (optional):",
        "trim_from": "From",
        "trim_to": "To",
        "trim_ph": "hh:mm:ss",
        "lbl_audio": "Audio:",
        "audio_copy": "Keep original",
        "output_to": "Save to:",
        "output_default": "Next to source (default)",
        "btn_reset_output": "Default",
        "btn_choose_output": "Choose folder",
        "lbl_progress": "Compression progress:",
        "btn_start": "🚀 START COMPRESSING",
        "btn_start_running": "Working, please wait...",
        "btn_cancel": "✖ CANCEL",
        "btn_cancel_running": "Cancelling...",
        "status_waiting": "waiting",
        "status_compressing": "compressing",
        "status_done": "done",
        "status_failed": "failed",
        "status_skipped": "skipped",
        "warn_no_files": "Please select a video before compressing!",
        "warn_bad_target": "Please enter a valid target size (a number of MB > 0).",
        "warn_bad_trim": "Invalid trim times. Use hh:mm:ss and 'To' must be greater than 'From'.",
        "warn_dialog_title": "Warning",
        "drop_invalid": "No valid video files found in the dropped items.",
        "preparing": "Preparing...",
        "compressing": "Compressing...",
        "compressing_gpu": "Compressing (GPU)...",
        "pass1": "Pass 1/2 (analyze)...",
        "pass2": "Pass 2/2 (encode)...",
        "file_done": "Finishing file...",
        "cancelled": "⏹ Compression cancelled.",
        "done_all": "✅ DONE! Compressed {ok}/{total} videos. {savings}",
        "partial": "⚠ Finished: {ok}/{total} videos OK, the rest failed (see log). {savings}",
        "none_done": "❌ No videos could be compressed (see log).",
        "sys_error": "❌ System error: {err}",
        "savings": "Total: {in_mb:.1f}MB ➡️ {out_mb:.1f}MB (saved {pct:.0f}%)",
        "eta": " • ~{eta} left",
    },
}


def tr(lang, key, **kwargs):
    """Lấy chuỗi dịch theo ngôn ngữ; fallback sang tiếng Việt nếu thiếu."""
    table = TRANSLATIONS.get(lang, TRANSLATIONS["vi"])
    text = table.get(key, TRANSLATIONS["vi"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# ---------- Hàm logic thuần (tách riêng để dễ test, không phụ thuộc GUI) ----------
def make_output_path(input_path, exists=os.path.exists, output_dir=None):
    """Tạo đường dẫn đầu ra, tránh ghi đè file đã tồn tại.
    `exists` cho phép thay hàm kiểm tra tồn tại khi test.
    `output_dir` nếu được đặt sẽ là thư mục lưu kết quả; mặc định lưu cạnh
    file gốc."""
    file_dir, file_name = os.path.split(input_path)
    if output_dir:
        file_dir = output_dir
    name, ext = os.path.splitext(file_name)
    candidate = os.path.join(file_dir, f"{name}_da_nen{ext}")
    counter = 1
    while exists(candidate):
        candidate = os.path.join(file_dir, f"{name}_da_nen ({counter}){ext}")
        counter += 1
    return candidate


def format_size(num_bytes):
    """Định dạng số byte sang chuỗi dễ đọc (KB/MB/GB)."""
    if num_bytes is None or num_bytes < 0:
        return "—"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)}{unit}"
            return f"{size:.1f}{unit}"
        size /= 1024


def is_video_file(path):
    """True nếu phần mở rộng nằm trong danh sách video hỗ trợ."""
    return os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS


def parse_dropped_files(raw, splitter=None):
    """Tách chuỗi dữ liệu kéo-thả thành danh sách đường dẫn video hợp lệ.

    `raw` là chuỗi do tkinterdnd2 cung cấp (các path ngăn cách bởi khoảng trắng,
    path chứa khoảng trắng được bọc trong {}). `splitter` cho phép thay hàm tách
    (mặc định tự xử lý cú pháp {} khi không có Tk)."""
    if splitter is not None:
        items = splitter(raw)
    else:
        items = _split_brace_list(raw)
    return [p for p in items if is_video_file(p)]


def _split_brace_list(raw):
    """Tách chuỗi kiểu Tcl list ('{a b} c') thành các phần tử, hỗ trợ {}."""
    items = []
    token = ""
    depth = 0
    for ch in raw:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                continue
        if ch == " " and depth == 0:
            if token:
                items.append(token)
                token = ""
            continue
        token += ch
    if token:
        items.append(token)
    return items


def format_eta(seconds):
    """Định dạng số giây còn lại thành mm:ss (hoặc h:mm:ss)."""
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_savings(in_bytes, out_bytes):
    """Tạo chuỗi tóm tắt tổng dung lượng trước/sau và % tiết kiệm.
    Trả về chuỗi rỗng nếu dung lượng gốc không hợp lệ."""
    if in_bytes <= 0:
        return ""
    in_mb = in_bytes / (1024 * 1024)
    out_mb = out_bytes / (1024 * 1024)
    saved_pct = (1 - out_bytes / in_bytes) * 100
    return f"Tổng: {in_mb:.1f}MB ➡️ {out_mb:.1f}MB (tiết kiệm {saved_pct:.0f}%)"


def load_config(path=CONFIG_PATH):
    """Đọc config.json. Trả về dict rỗng nếu không có/đọc lỗi."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_config(data, path=CONFIG_PATH):
    """Ghi dict cấu hình ra file JSON. Trả về True nếu thành công."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def parse_time_to_seconds(text):
    """Đổi chuỗi thời gian sang số giây. Hỗ trợ 'SS', 'MM:SS', 'HH:MM:SS'
    và số thập phân. Trả về None nếu rỗng/không hợp lệ, hoặc số âm."""
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    parts = text.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 1:
        seconds = parts[0]
    elif len(parts) == 2:
        seconds = parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        return None
    return seconds if seconds >= 0 else None


def trim_args(ss=None, to=None):
    """Tham số cắt video cho FFmpeg (đặt SAU -i để cắt chính xác theo frame)."""
    args = []
    if ss:
        args += ['-ss', str(ss)]
    if to:
        args += ['-to', str(to)]
    return args


def audio_args(audio_bitrate="128k"):
    """Tham số audio: 'copy' để giữ nguyên, ngược lại mã hoá AAC ở bitrate cho trước."""
    if audio_bitrate == "copy":
        return ['-c:a', 'copy']
    return ['-c:a', 'aac', '-b:a', audio_bitrate]


def build_ffmpeg_command(input_path, output_path, crf_value, vcodec, force_720p,
                         preset="fast", ss=None, to=None, audio_bitrate="128k"):
    """Dựng danh sách tham số dòng lệnh FFmpeg cho chế độ chất lượng một lượt
    (hàm thuần, dễ test).

    Encoder CPU (libx264/265) dùng `-crf`; encoder phần cứng NVENC dùng
    `-cq` (constant quality) và preset dạng p1..p7. Hỗ trợ cắt video (ss/to)
    và chọn bitrate audio."""
    command = ['ffmpeg', '-y', '-i', input_path, *trim_args(ss, to), '-vcodec', vcodec]
    if is_hardware_encoder(vcodec):
        command += ['-rc', 'vbr', '-cq', str(crf_value), '-preset', nvenc_preset(preset)]
    else:
        command += ['-crf', str(crf_value), '-preset', preset]
    if force_720p:
        command += ['-vf', 'scale=-2:720']
    command += [*audio_args(audio_bitrate), '-progress', 'pipe:1', '-nostats', output_path]
    return command


def is_hardware_encoder(vcodec):
    """True nếu là encoder tăng tốc phần cứng (NVENC/QSV/AMF)."""
    return vcodec.endswith(("_nvenc", "_qsv", "_amf"))


# Ánh xạ preset kiểu x264 (nhanh->chậm) sang preset NVENC p1..p7
_NVENC_PRESET_MAP = {
    "ultrafast": "p1", "superfast": "p1", "veryfast": "p2", "faster": "p3",
    "fast": "p4", "medium": "p4", "slow": "p5", "slower": "p6", "veryslow": "p7",
}


def nvenc_preset(cpu_preset):
    """Đổi preset kiểu x264 sang preset tương đương của NVENC (mặc định p4)."""
    return _NVENC_PRESET_MAP.get(cpu_preset, "p4")


def build_nvenc_abr_command(input_path, output_path, vcodec, bitrate_kbps,
                            force_720p, preset, ss=None, to=None, audio_bitrate="128k"):
    """Dựng lệnh NVENC một lượt theo bitrate trung bình (xấp xỉ dung lượng
    mục tiêu). NVENC không dùng 2-pass kiểu log như CPU nên ta giới hạn
    maxrate/bufsize để bám sát mục tiêu."""
    scale = ['-vf', 'scale=-2:720'] if force_720p else []
    maxrate = int(bitrate_kbps * 1.5)
    bufsize = bitrate_kbps * 2
    return [
        'ffmpeg', '-y', '-i', input_path, *trim_args(ss, to),
        '-c:v', vcodec, '-rc', 'vbr',
        '-b:v', f'{bitrate_kbps}k',
        '-maxrate', f'{maxrate}k', '-bufsize', f'{bufsize}k',
        '-preset', nvenc_preset(preset), *scale,
        *audio_args(audio_bitrate),
        '-progress', 'pipe:1', '-nostats',
        output_path,
    ]


def detect_available_encoders(runner=subprocess.run, candidates=("h264_nvenc", "hevc_nvenc")):
    """Dò các encoder GPU THỰC SỰ dùng được. Encoder có thể được biên dịch
    sẵn trong FFmpeg nhưng vẫn lỗi lúc chạy nếu thiếu driver/phần cứng
    (vd 'Cannot load nvcuda.dll'), nên ta thử encode 1 frame để chắc chắn."""
    return {enc for enc in candidates if _probe_encoder(enc, runner)}


def _probe_encoder(encoder, runner=subprocess.run):
    """Thử mở encoder bằng cách mã hoá 1 frame ra null. True nếu thành công."""
    try:
        result = runner(
            [
                'ffmpeg', '-hide_banner',
                '-f', 'lavfi', '-i', 'nullsrc=s=256x144:d=0.1',
                '-c:v', encoder, '-frames:v', '1',
                '-f', 'null', os.devnull,
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
    except Exception:
        return False
    return getattr(result, "returncode", 1) == 0


def format_size_change(in_bytes, out_bytes):
    """Mô tả thay đổi dung lượng sau nén. Trả về (text, grew) với grew=True
    khi file sau nén KHÔNG nhỏ hơn file gốc (cảnh báo)."""
    before = format_size(in_bytes)
    after = format_size(out_bytes)
    if in_bytes <= 0:
        return f"{before} ➡️ {after}", False
    if out_bytes >= in_bytes:
        grew_pct = (out_bytes / in_bytes - 1) * 100
        return f"⚠ {before} ➡️ {after} (+{grew_pct:.0f}%)", True
    saved = (1 - out_bytes / in_bytes) * 100
    return f"{before} ➡️ {after} (-{saved:.0f}%)", False


def compute_video_bitrate(target_mb, duration_sec, audio_kbps=128, min_video_kbps=100):
    """Tính bitrate video (kbps) để file đầu ra xấp xỉ `target_mb` MB.

    Trả về None nếu không tính được (thiếu độ dài) hoặc mục tiêu quá nhỏ
    đến mức không còn đủ bitrate hợp lý cho video.
    Quy ước: 1 MB ≈ 8192 kbit; trừ phần dành cho audio."""
    if target_mb <= 0 or duration_sec <= 0:
        return None
    total_kbps = (target_mb * 8192) / duration_sec
    video_kbps = int(total_kbps - audio_kbps)
    if video_kbps < min_video_kbps:
        return None
    return video_kbps


def build_two_pass_commands(input_path, output_path, vcodec, bitrate_kbps,
                            force_720p, preset, passlogfile, null_path=os.devnull,
                            ss=None, to=None, audio_bitrate="128k"):
    """Dựng cặp lệnh FFmpeg 2-pass cho chế độ nén theo dung lượng mục tiêu.

    Trả về (cmd_pass1, cmd_pass2). Pass 1 phân tích và bỏ audio, ghi ra
    null; pass 2 mã hoá thật kèm audio."""
    scale = ['-vf', 'scale=-2:720'] if force_720p else []
    trim = trim_args(ss, to)
    pass1 = [
        'ffmpeg', '-y', '-i', input_path, *trim,
        '-c:v', vcodec, '-b:v', f'{bitrate_kbps}k',
        '-preset', preset, *scale,
        '-pass', '1', '-passlogfile', passlogfile,
        '-an', '-f', 'null',
        '-progress', 'pipe:1', '-nostats',
        null_path,
    ]
    pass2 = [
        'ffmpeg', '-y', '-i', input_path, *trim,
        '-c:v', vcodec, '-b:v', f'{bitrate_kbps}k',
        '-preset', preset, *scale,
        '-pass', '2', '-passlogfile', passlogfile,
        *audio_args(audio_bitrate),
        '-progress', 'pipe:1', '-nostats',
        output_path,
    ]
    return pass1, pass2


def parse_progress_fraction(line, total_duration):
    """Đọc một dòng `-progress` của FFmpeg, trả về phần trăm (0..1) đã nén.

    Trả về None nếu dòng không phải `out_time_ms=` hợp lệ hoặc không tính được
    (ví dụ total_duration <= 0)."""
    line = line.strip()
    if not line.startswith('out_time_ms=') or total_duration <= 0:
        return None
    try:
        out_time_ms = int(line.split('=', 1)[1])
    except ValueError:
        return None
    fraction = (out_time_ms / 1_000_000) / total_duration
    return max(0.0, min(fraction, 1.0))


class VideoCompressorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Bật hỗ trợ kéo-thả file (nếu tkinterdnd2 có sẵn). CTk kế thừa tk.Tk
        # nên ta nạp engine TkDnD trực tiếp lên instance.
        self.dnd_enabled = False
        if _DND_AVAILABLE:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd_enabled = True
            except Exception:
                self.dnd_enabled = False

        self.geometry("660x820")
        self.minsize(620, 600)

        # Danh sách file đầu vào (hỗ trợ nén hàng loạt)
        self.input_files = []
        self.output_file = ""   # file đầu ra đang xử lý
        self.row_widgets = {}   # input_path -> {"frame":, "status":, "size":}

        # Trạng thái tiến trình nén
        self.process = None        # tham chiếu tới tiến trình ffmpeg đang chạy
        self.is_cancelled = False  # cờ đánh dấu người dùng đã bấm Hủy
        self.is_running = False    # cờ đang nén (khoá thao tác sửa danh sách)
        self.batch_start_time = 0  # mốc thời gian bắt đầu cả lô (để tính ETA)

        # Danh sách codec khả dụng = CPU + GPU (nếu máy hỗ trợ NVENC).
        # Lưu theo khoá nhãn (để dịch) và bản đồ khoá -> encoder.
        self._all_codecs = {**CODECS, **GPU_CODECS}
        self.available_codec_keys = list(CODECS.keys())
        gpu = detect_available_encoders()
        for key, enc in GPU_CODECS.items():
            if enc in gpu:
                self.available_codec_keys.append(key)

        # Đọc cấu hình đã lưu (nếu có)
        self.config = self.load_config()
        self.last_dir = self.config.get("last_dir", "")
        # Ngôn ngữ giao diện
        self.lang = self.config.get("lang", "vi")
        if self.lang not in LANGUAGES:
            self.lang = "vi"
        # Thư mục lưu kết quả riêng ("" = lưu cạnh file gốc như mặc định)
        self.output_dir = self.config.get("output_dir", "")
        if self.output_dir and not os.path.isdir(self.output_dir):
            self.output_dir = ""

        self.build_ui()
        self.apply_config()
        self.title(self.t("title"))

        # Lưu cấu hình khi đóng cửa sổ
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- i18n ----------
    def t(self, key, **kwargs):
        """Lấy chuỗi dịch theo ngôn ngữ hiện tại."""
        return tr(self.lang, key, **kwargs)

    def current_mode(self):
        """Token chế độ hiện tại (MODE_CRF / MODE_SIZE), độc lập ngôn ngữ."""
        return self.mode_label_to_token.get(self.mode_selector.get(), MODE_CRF)

    def current_encoder(self):
        """Tham số encoder FFmpeg ứng với codec đang chọn."""
        return self.codec_label_to_enc.get(self.codec_selector.get(), "libx265")

    def current_audio_bitrate(self):
        """Giá trị audio bitrate đang chọn ('96k'.. hoặc 'copy')."""
        return self.audio_label_to_val.get(self.audio_selector.get(), "128k")

    def change_language(self, label):
        """Đổi ngôn ngữ và dựng lại toàn bộ giao diện."""
        new_lang = self.lang_label_to_code.get(label, "vi")
        if new_lang == self.lang:
            return
        self.config = self.build_config_dict()
        self.lang = new_lang
        for child in self.winfo_children():
            child.destroy()
        self.build_ui()
        self.apply_config()
        self.title(self.t("title"))
        if self.input_files:
            self._refresh_file_path_label()
            self.rebuild_file_list()

    # ---------- Cấu hình ----------
    def load_config(self):
        """Đọc config.json (dùng hàm logic thuần cấp module)."""
        return load_config(CONFIG_PATH)

    def build_config_dict(self):
        """Gom toàn bộ lựa chọn hiện tại thành dict (khoá độc lập ngôn ngữ)."""
        return {
            "lang": self.lang,
            "codec": self.current_encoder(),     # lưu theo encoder (ổn định)
            "crf": int(self.slider_quality.get()),
            "force_720p": bool(self.check_720p.get()),
            "preset": self.preset_selector.get(),
            "mode": self.current_mode(),          # token "crf"/"size"
            "target_mb": self.entry_target.get().strip(),
            "audio": self.current_audio_bitrate(),
            "trim_enabled": bool(self.check_trim.get()),
            "trim_from": self.entry_trim_from.get().strip(),
            "trim_to": self.entry_trim_to.get().strip(),
            "last_dir": self.last_dir,
            "output_dir": self.output_dir,
        }

    def save_config(self):
        """Ghi lựa chọn hiện tại ra config.json để lần sau khỏi chỉnh lại."""
        save_config(self.build_config_dict(), CONFIG_PATH)

    def apply_config(self):
        """Áp các giá trị đã lưu lên widget khi mở app (hoặc sau khi đổi ngôn ngữ)."""
        cfg = self.config

        # Codec: tìm nhãn ứng với encoder đã lưu
        enc = cfg.get("codec")
        for label, e in self.codec_label_to_enc.items():
            if e == enc:
                self.codec_selector.set(label)
                break

        crf = cfg.get("crf")
        if isinstance(crf, (int, float)) and 18 <= crf <= 50:
            self.slider_quality.set(int(crf))
        self.update_crf_label(int(self.slider_quality.get()))

        if cfg.get("force_720p"):
            self.check_720p.select()

        preset = cfg.get("preset")
        if preset in PRESETS:
            self.preset_selector.set(preset)

        mode = cfg.get("mode")
        if mode in self.mode_token_to_label:
            self.mode_selector.set(self.mode_token_to_label[mode])

        target = cfg.get("target_mb")
        if isinstance(target, str) and target:
            self.entry_target.delete(0, "end")
            self.entry_target.insert(0, target)

        audio = cfg.get("audio")
        if audio in AUDIO_BITRATES:
            label = self.t("audio_copy") if audio == "copy" else audio
            self.audio_selector.set(label)

        if cfg.get("trim_enabled"):
            self.check_trim.select()
        for entry, key in ((self.entry_trim_from, "trim_from"), (self.entry_trim_to, "trim_to")):
            val = cfg.get(key)
            if isinstance(val, str) and val:
                entry.delete(0, "end")
                entry.insert(0, val)

        # Hiển thị thư mục output + đồng bộ trạng thái theo chế độ/cắt
        self.update_output_dir_label()
        self._apply_mode_state()
        self._apply_trim_state()

    def on_close(self):
        """Lưu cấu hình rồi đóng app."""
        self.save_config()
        self.destroy()

    def build_ui(self):
        # Thanh trên cùng: chọn ngôn ngữ (ngoài vùng cuộn)
        self.lang_label_to_code = {"Tiếng Việt": "vi", "English": "en"}
        code_to_label = {v: k for k, v in self.lang_label_to_code.items()}
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=20, pady=(10, 0))
        self.lang_selector = ctk.CTkOptionMenu(
            self.top_bar, values=list(self.lang_label_to_code.keys()),
            width=130, command=self.change_language
        )
        self.lang_selector.set(code_to_label.get(self.lang, "Tiếng Việt"))
        self.lang_selector.pack(side="right")
        self.lbl_lang = ctk.CTkLabel(self.top_bar, text=self.t("lang_label"))
        self.lbl_lang.pack(side="right", padx=(0, 6))

        # Vùng nội dung cuộn được (tránh tràn khi có nhiều tuỳ chọn)
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Tiêu đề
        self.lbl_title = ctk.CTkLabel(body, text=self.t("header"), font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=(4, 6))
        self.lbl_subtitle = ctk.CTkLabel(body, text=self.t("subtitle"), font=("Roboto", 13), text_color="gray")
        self.lbl_subtitle.pack(pady=(0, 12))

        # Khung chọn file
        self.frame_file = ctk.CTkFrame(body)
        self.frame_file.pack(pady=8, padx=20, fill="x")
        self.lbl_file_path = ctk.CTkLabel(self.frame_file, text=self.t("file_none"), width=360, anchor="w")
        self.lbl_file_path.pack(side="left", padx=10, pady=10)
        self.btn_select = ctk.CTkButton(self.frame_file, text=self.t("btn_select"), command=self.select_files, width=110)
        self.btn_select.pack(side="right", padx=(5, 10), pady=10)
        self.btn_clear = ctk.CTkButton(
            self.frame_file, text=self.t("btn_clear"), command=self.clear_files, width=110,
            fg_color="#5a5a5a", hover_color="#454545", state="disabled"
        )
        self.btn_clear.pack(side="right", padx=(10, 0), pady=10)

        # Danh sách file
        list_label = self.t("list_label_dnd") if self.dnd_enabled else self.t("list_label")
        self.frame_list = ctk.CTkScrollableFrame(body, height=120, label_text=list_label)
        self.frame_list.pack(pady=8, padx=20, fill="x")
        self._register_drop_target()

        # Codec
        self.frame_codec = ctk.CTkFrame(body)
        self.frame_codec.pack(pady=6, padx=20, fill="x")
        self.lbl_codec = ctk.CTkLabel(self.frame_codec, text=self.t("lbl_codec"))
        self.lbl_codec.pack(side="left", padx=10, pady=10)
        self.codec_label_to_enc = {}
        codec_values = []
        for key in self.available_codec_keys:
            label = self.t(key)
            self.codec_label_to_enc[label] = self._all_codecs[key]
            codec_values.append(label)
        self.codec_selector = ctk.CTkSegmentedButton(self.frame_codec, values=codec_values)
        self.codec_selector.set(self.t("codec_h265"))
        self.codec_selector.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        # Preset tốc độ + audio bitrate (chung một hàng)
        self.frame_preset = ctk.CTkFrame(body)
        self.frame_preset.pack(pady=6, padx=20, fill="x")
        self.lbl_preset = ctk.CTkLabel(self.frame_preset, text=self.t("lbl_preset"))
        self.lbl_preset.pack(side="left", padx=10, pady=10)
        self.preset_selector = ctk.CTkOptionMenu(self.frame_preset, values=PRESETS, width=120)
        self.preset_selector.set("fast")
        self.preset_selector.pack(side="left", padx=(0, 12), pady=10)
        self.lbl_audio = ctk.CTkLabel(self.frame_preset, text=self.t("lbl_audio"))
        self.lbl_audio.pack(side="left", padx=(6, 0), pady=10)
        self.audio_label_to_val = {}
        audio_values = []
        for b in AUDIO_BITRATES:
            label = self.t("audio_copy") if b == "copy" else b
            self.audio_label_to_val[label] = b
            audio_values.append(label)
        self.audio_selector = ctk.CTkOptionMenu(self.frame_preset, values=audio_values, width=120)
        self.audio_selector.set("128k")
        self.audio_selector.pack(side="left", padx=6, pady=10)

        # Chế độ nén
        self.frame_mode = ctk.CTkFrame(body)
        self.frame_mode.pack(pady=6, padx=20, fill="x")
        self.lbl_mode = ctk.CTkLabel(self.frame_mode, text=self.t("lbl_mode"))
        self.lbl_mode.pack(side="left", padx=10, pady=10)
        self.mode_label_to_token = {self.t("mode_crf"): MODE_CRF, self.t("mode_size"): MODE_SIZE}
        self.mode_token_to_label = {v: k for k, v in self.mode_label_to_token.items()}
        self.mode_selector = ctk.CTkSegmentedButton(
            self.frame_mode, values=[self.t("mode_crf"), self.t("mode_size")], command=self.on_mode_change
        )
        self.mode_selector.set(self.t("mode_crf"))
        self.mode_selector.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        # Dung lượng mục tiêu
        self.frame_target = ctk.CTkFrame(body)
        self.frame_target.pack(pady=0, padx=20, fill="x")
        self.lbl_target = ctk.CTkLabel(self.frame_target, text=self.t("lbl_target"))
        self.lbl_target.pack(side="left", padx=10, pady=10)
        self.entry_target = ctk.CTkEntry(self.frame_target, width=90, placeholder_text="MB")
        self.entry_target.pack(side="left", padx=6, pady=10)
        self.lbl_target_unit = ctk.CTkLabel(self.frame_target, text=self.t("target_unit"), text_color="gray")
        self.lbl_target_unit.pack(side="left", padx=4, pady=10)

        # Mức nén (CRF)
        self.frame_quality = ctk.CTkFrame(body)
        self.frame_quality.pack(pady=6, padx=20, fill="x")
        self.lbl_quality = ctk.CTkLabel(self.frame_quality, text=self.t("lbl_quality"))
        self.lbl_quality.pack(side="left", padx=10, pady=10)
        self.slider_quality = ctk.CTkSlider(self.frame_quality, from_=18, to=50, number_of_steps=32)
        self.slider_quality.set(28)
        self.slider_quality.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.lbl_crf_val = ctk.CTkLabel(self.frame_quality, text="")
        self.lbl_crf_val.pack(side="right", padx=10, pady=10)
        self.slider_quality.configure(command=lambda v: self.update_crf_label(v))

        # Ép 720p
        self.frame_options = ctk.CTkFrame(body)
        self.frame_options.pack(pady=0, padx=20, fill="x")
        self.check_720p = ctk.CTkCheckBox(self.frame_options, text=self.t("check_720p"))
        self.check_720p.pack(side="left", padx=10, pady=10)

        # Cắt video theo thời gian
        self.frame_trim = ctk.CTkFrame(body)
        self.frame_trim.pack(pady=6, padx=20, fill="x")
        self.check_trim = ctk.CTkCheckBox(self.frame_trim, text=self.t("lbl_trim"), command=self._apply_trim_state)
        self.check_trim.pack(side="left", padx=10, pady=10)
        self.lbl_trim_from = ctk.CTkLabel(self.frame_trim, text=self.t("trim_from"))
        self.lbl_trim_from.pack(side="left", padx=(6, 2), pady=10)
        self.entry_trim_from = ctk.CTkEntry(self.frame_trim, width=90, placeholder_text=self.t("trim_ph"))
        self.entry_trim_from.pack(side="left", padx=2, pady=10)
        self.lbl_trim_to = ctk.CTkLabel(self.frame_trim, text=self.t("trim_to"))
        self.lbl_trim_to.pack(side="left", padx=(8, 2), pady=10)
        self.entry_trim_to = ctk.CTkEntry(self.frame_trim, width=90, placeholder_text=self.t("trim_ph"))
        self.entry_trim_to.pack(side="left", padx=2, pady=10)

        # Thư mục lưu kết quả
        self.frame_output = ctk.CTkFrame(body)
        self.frame_output.pack(pady=6, padx=20, fill="x")
        self.lbl_output_caption = ctk.CTkLabel(self.frame_output, text=self.t("output_to"))
        self.lbl_output_caption.pack(side="left", padx=10, pady=10)
        self.lbl_output_dir = ctk.CTkLabel(
            self.frame_output, text=self.t("output_default"), anchor="w", text_color="gray"
        )
        self.lbl_output_dir.pack(side="left", padx=4, pady=10, expand=True, fill="x")
        self.btn_reset_output = ctk.CTkButton(
            self.frame_output, text=self.t("btn_reset_output"), command=self.reset_output_dir, width=90,
            fg_color="#5a5a5a", hover_color="#454545"
        )
        self.btn_reset_output.pack(side="right", padx=(5, 10), pady=10)
        self.btn_choose_output = ctk.CTkButton(
            self.frame_output, text=self.t("btn_choose_output"), command=self.choose_output_dir, width=120
        )
        self.btn_choose_output.pack(side="right", padx=(5, 0), pady=10)

        # Thanh tiến trình
        self.lbl_progress = ctk.CTkLabel(body, text=self.t("lbl_progress"), anchor="w")
        self.lbl_progress.pack(pady=(8, 0), padx=20, fill="x")
        self.progress_bar = ctk.CTkProgressBar(
            body, mode="determinate", height=20, progress_color="#1f6aa5", fg_color="#4a4a4a"
        )
        self.progress_bar.pack(pady=(2, 12), padx=20, fill="x")
        self.progress_bar.set(0)

        # Nút hành động
        self.frame_actions = ctk.CTkFrame(body, fg_color="transparent")
        self.frame_actions.pack(pady=8, padx=20, fill="x")
        self.btn_start = ctk.CTkButton(
            self.frame_actions, text=self.t("btn_start"), font=("Roboto", 16, "bold"),
            height=50, command=self.start_compression
        )
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.btn_cancel = ctk.CTkButton(
            self.frame_actions, text=self.t("btn_cancel"), font=("Roboto", 16, "bold"), height=50,
            width=110, fg_color="#a83232", hover_color="#8a2929",
            command=self.cancel_compression, state="disabled"
        )
        self.btn_cancel.pack(side="right", padx=(5, 0))

        # Trạng thái
        self.lbl_status = ctk.CTkLabel(body, text="", text_color="green", font=("Roboto", 14), wraplength=600)
        self.lbl_status.pack(pady=(8, 16))

    def update_crf_label(self, value):
        value = int(float(value))
        if value < 23:
            txt = self.t("crf_big", v=value)
        elif value > 35:
            txt = self.t("crf_strong", v=value)
        else:
            txt = self.t("crf_rec", v=value)
        self.lbl_crf_val.configure(text=txt)

    def on_mode_change(self, _value=None):
        """Bật/tắt widget tuỳ chế độ: CRF dùng slider, Target size dùng ô MB."""
        self._apply_mode_state()

    def _apply_mode_state(self):
        """Đồng bộ trạng thái enable/disable của slider CRF và ô dung lượng."""
        is_size = self.current_mode() == MODE_SIZE
        self.slider_quality.configure(state="disabled" if is_size else "normal")
        self.entry_target.configure(state="normal" if is_size else "disabled")
        self.lbl_quality.configure(text_color="gray" if is_size else "white")
        self.lbl_target.configure(text_color="white" if is_size else "gray")
        self.lbl_target_unit.configure(text_color="gray")

    def _apply_trim_state(self):
        """Bật/tắt ô nhập mốc cắt theo checkbox 'Cắt video'."""
        on = bool(self.check_trim.get())
        state = "normal" if on else "disabled"
        self.entry_trim_from.configure(state=state)
        self.entry_trim_to.configure(state=state)
        color = "white" if on else "gray"
        self.lbl_trim_from.configure(text_color=color)
        self.lbl_trim_to.configure(text_color=color)

    def _refresh_file_path_label(self):
        """Cập nhật nhãn đường dẫn theo số file đang chọn."""
        if not self.input_files:
            self.lbl_file_path.configure(text=self.t("file_none"))
        elif len(self.input_files) == 1:
            self.lbl_file_path.configure(text=os.path.basename(self.input_files[0]))
        else:
            self.lbl_file_path.configure(text=self.t("file_many", n=len(self.input_files)))

    # ---------- Kéo & thả ----------
    def _register_drop_target(self):
        """Đăng ký vùng danh sách nhận file kéo-thả (nếu bật được DnD)."""
        if not self.dnd_enabled:
            return
        try:
            self.frame_list.drop_target_register(DND_FILES)
            self.frame_list.dnd_bind("<<Drop>>", self.on_drop)
        except Exception:
            self.dnd_enabled = False

    def on_drop(self, event):
        """Xử lý sự kiện thả file: lọc lấy video hợp lệ rồi nạp vào danh sách."""
        files = parse_dropped_files(event.data, splitter=self.tk.splitlist)
        if not files:
            self.lbl_status.configure(text=self.t("drop_invalid"), text_color="orange")
            return
        self._set_input_files(files)

    # ---------- Thư mục output ----------
    def update_output_dir_label(self):
        """Cập nhật nhãn hiển thị thư mục lưu kết quả."""
        if self.output_dir:
            self.lbl_output_dir.configure(text=self.output_dir, text_color="white")
        else:
            self.lbl_output_dir.configure(text=self.t("output_default"), text_color="gray")

    def choose_output_dir(self):
        """Cho người dùng chọn thư mục lưu kết quả riêng."""
        initial = self.output_dir if self.output_dir and os.path.isdir(self.output_dir) else None
        chosen = filedialog.askdirectory(title="Chọn thư mục lưu video đã nén", initialdir=initial)
        if chosen:
            self.output_dir = chosen
            self.update_output_dir_label()

    def reset_output_dir(self):
        """Quay về mặc định: lưu cạnh file gốc."""
        self.output_dir = ""
        self.update_output_dir_label()

    # ---------- Danh sách file ----------
    def rebuild_file_list(self):
        """Vẽ lại danh sách file với trạng thái ban đầu là 'chờ'."""
        # Xóa các dòng cũ
        for child in self.frame_list.winfo_children():
            child.destroy()
        self.row_widgets = {}

        for path in self.input_files:
            row = ctk.CTkFrame(self.frame_list)
            row.pack(fill="x", pady=2, padx=2)

            lbl_name = ctk.CTkLabel(row, text=os.path.basename(path), anchor="w")
            lbl_name.pack(side="left", padx=8, pady=4, expand=True, fill="x")

            # Nút xoá file này khỏi danh sách (vô hiệu khi đang nén)
            btn_remove = ctk.CTkButton(
                row, text="✕", width=28, fg_color="#5a5a5a", hover_color="#7a3030",
                command=lambda p=path: self.remove_file(p)
            )
            btn_remove.pack(side="right", padx=(0, 6), pady=4)

            # Dung lượng gốc của file (sẽ đổi thành "gốc ➡️ sau" khi nén xong)
            try:
                orig = format_size(os.path.getsize(path))
            except OSError:
                orig = "—"
            lbl_size = ctk.CTkLabel(row, text=orig, width=150, anchor="e", text_color="gray")
            lbl_size.pack(side="right", padx=4, pady=4)

            lbl_status = ctk.CTkLabel(row, text=f"● {self.t('status_waiting')}", width=90, anchor="e", text_color=STATUS_COLORS[STATUS_WAITING])
            lbl_status.pack(side="right", padx=8, pady=4)

            self.row_widgets[path] = {"frame": row, "status": lbl_status, "size": lbl_size}

    def remove_file(self, path):
        """Xoá một file khỏi danh sách (không xoá trên ổ đĩa). Bị khoá khi đang nén."""
        if self.is_running:
            return
        if path in self.input_files:
            self.input_files.remove(path)
        if not self.input_files:
            self.clear_files()
            return
        self._refresh_file_path_label()
        self.rebuild_file_list()

    def set_file_status(self, path, status):
        """Cập nhật nhãn trạng thái (status là token độc lập ngôn ngữ)."""
        widget = self.row_widgets.get(path)
        if widget:
            widget["status"].configure(
                text=f"● {self.t('status_' + status)}",
                text_color=STATUS_COLORS.get(status, "gray")
            )

    def set_file_result(self, path, in_bytes, out_bytes):
        """Hiện dung lượng trước/sau cho một file sau khi nén xong.
        Cảnh báo (màu vàng) nếu file sau nén không nhỏ hơn file gốc."""
        widget = self.row_widgets.get(path)
        if widget:
            text, grew = format_size_change(in_bytes, out_bytes)
            widget["size"].configure(text=text, text_color="#e0a82f" if grew else "#3ba55d")

    # ---------- Chọn file ----------
    def select_files(self):
        filetypes = (
            ('Video files', '*.mp4 *.mkv *.avi *.mov *.flv'),
            ('All files', '*.*')
        )
        initial = self.last_dir if self.last_dir and os.path.isdir(self.last_dir) else None
        filenames = filedialog.askopenfilenames(
            title="Chọn video gốc (có thể chọn nhiều)",
            filetypes=filetypes,
            initialdir=initial
        )
        if filenames:
            self._set_input_files(list(filenames))

    def _set_input_files(self, files):
        """Nạp danh sách file mới vào UI (dùng chung cho dialog và kéo-thả)."""
        self.input_files = list(files)
        self.last_dir = os.path.dirname(self.input_files[0])
        self._refresh_file_path_label()
        self.rebuild_file_list()
        self.btn_clear.configure(state="normal")
        self.lbl_status.configure(text="")
        self.progress_bar.stop()
        self.progress_bar.set(0)

    def clear_files(self):
        """Xóa toàn bộ danh sách file đã chọn (không xóa file trên ổ đĩa)."""
        self.input_files = []
        self.output_file = ""
        for child in self.frame_list.winfo_children():
            child.destroy()
        self.row_widgets = {}
        self.lbl_file_path.configure(text=self.t("file_none"))
        self.btn_clear.configure(state="disabled")
        self.lbl_status.configure(text="")
        self.progress_bar.stop()
        self.progress_bar.set(0)

    # ---------- Kiểm tra file ----------
    def validate_input_file(self, path):
        """Kiểm tra một file có tồn tại và có phải video thật không.
        Trả về (True, "") nếu hợp lệ, ngược lại (False, thông báo lỗi)."""
        if not os.path.exists(path):
            return False, "File không còn tồn tại."
        if os.path.getsize(path) == 0:
            return False, "File rỗng (0 byte)."
        try:
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=codec_type',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    path
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if 'video' not in result.stdout.decode('utf-8', errors='ignore'):
                return False, "Không chứa luồng video hợp lệ (có thể hỏng/sai định dạng)."
        except FileNotFoundError:
            return False, "Không tìm thấy ffprobe để kiểm tra file."
        except subprocess.TimeoutExpired:
            return False, "Quá thời gian kiểm tra file (ffprobe không phản hồi)."
        return True, ""

    # ---------- Bắt đầu nén ----------
    def start_compression(self):
        if not self.input_files:
            messagebox.showwarning(self.t("warn_dialog_title"), self.t("warn_no_files"))
            return

        mode = self.current_mode()
        target_mb = None
        if mode == MODE_SIZE:
            raw = self.entry_target.get().strip().replace(",", ".")
            try:
                target_mb = float(raw)
                if target_mb <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(self.t("warn_dialog_title"), self.t("warn_bad_target"))
                return

        # Cắt video: kiểm tra mốc thời gian nếu bật
        trim_from = trim_to = None
        if self.check_trim.get():
            from_s = parse_time_to_seconds(self.entry_trim_from.get())
            to_s = parse_time_to_seconds(self.entry_trim_to.get())
            from_val = from_s if from_s is not None else 0.0
            # Hợp lệ khi có 'Đến' và lớn hơn 'Từ'
            if to_s is None or to_s <= from_val:
                messagebox.showwarning(self.t("warn_dialog_title"), self.t("warn_bad_trim"))
                return
            trim_from = self.entry_trim_from.get().strip() or "0"
            trim_to = self.entry_trim_to.get().strip()

        # Lưu cấu hình ngay khi bắt đầu (nhớ lựa chọn cho lần sau)
        self.save_config()

        self.is_cancelled = False
        self.is_running = True
        self.batch_start_time = time.time()

        for path in self.input_files:
            self.set_file_status(path, STATUS_WAITING)

        self.btn_start.configure(state="disabled", text=self.t("btn_start_running"))
        self.btn_select.configure(state="disabled")
        self.codec_selector.configure(state="disabled")
        self.preset_selector.configure(state="disabled")
        self.mode_selector.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.progress_bar.set(0)
        self.lbl_status.configure(text=self.t("preparing"), text_color="orange")

        opts = {
            "mode": mode,
            "crf": int(self.slider_quality.get()),
            "vcodec": self.current_encoder(),
            "force_720p": self.check_720p.get() == 1,
            "preset": self.preset_selector.get(),
            "target_mb": target_mb,
            "audio": self.current_audio_bitrate(),
            "ss": trim_from,
            "to": trim_to,
        }

        threading.Thread(
            target=self.run_batch,
            args=(list(self.input_files), opts),
            daemon=True
        ).start()

    def cancel_compression(self):
        """Hủy tiến trình nén đang chạy (dừng luôn cả lô)."""
        self.is_cancelled = True
        self.btn_cancel.configure(state="disabled", text=self.t("btn_cancel_running"))
        self.lbl_status.configure(text=self.t("cancelled"), text_color="gray")
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass

    # ---------- Tiện ích ----------
    def open_folder(self, path):
        """Mở thư mục chứa file đầu ra trên mọi nền tảng."""
        try:
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path])
            else:
                subprocess.run(['xdg-open', path])
        except Exception:
            pass

    def write_error_log(self, error_text):
        """Ghi toàn bộ lỗi FFmpeg ra file log để tiện debug."""
        try:
            log_dir = os.path.dirname(self.input_files[0]) if self.input_files else os.getcwd()
            log_path = os.path.join(log_dir, 'video_compressor_error.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(error_text + "\n" + ("-" * 60) + "\n")
            return log_path
        except Exception:
            return None

    def get_video_duration(self, path):
        """Lấy độ dài video (giây) bằng ffprobe để tính phần trăm tiến trình."""
        try:
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    path
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.decode('utf-8').strip())
        except (ValueError, FileNotFoundError, subprocess.TimeoutExpired):
            return 0.0

    @staticmethod
    def format_eta(seconds):
        """Định dạng số giây còn lại (uỷ thác cho hàm module)."""
        return format_eta(seconds)

    def make_output_path(self, input_path):
        """Tạo đường dẫn đầu ra, tránh ghi đè (uỷ thác cho hàm module).
        Dùng thư mục output riêng nếu người dùng đã chọn."""
        out_dir = self.output_dir if self.output_dir and os.path.isdir(self.output_dir) else None
        return make_output_path(input_path, output_dir=out_dir)

    def update_progress(self, overall_fraction, label_prefix):
        """Cập nhật thanh tiến trình tổng + nhãn % kèm ETA, an toàn từ luồng chính."""
        overall_fraction = max(0.0, min(overall_fraction, 1.0))
        self.progress_bar.set(overall_fraction)

        eta_text = ""
        elapsed = time.time() - self.batch_start_time
        if overall_fraction > 0.01 and elapsed > 1:
            total_est = elapsed / overall_fraction
            remaining = total_est - elapsed
            eta_text = self.t("eta", eta=self.format_eta(remaining))

        self.lbl_status.configure(
            text=f"{label_prefix} {int(overall_fraction * 100)}%{eta_text}",
            text_color="orange"
        )

    # ---------- Vòng nén hàng loạt ----------
    def run_batch(self, files, opts):
        total = len(files)
        success_count = 0
        total_in_bytes = 0
        total_out_bytes = 0
        try:
            for index, input_path in enumerate(files):
                if self.is_cancelled:
                    break

                prefix = f"[{index + 1}/{total}]" if total > 1 else ""

                valid, err_msg = self.validate_input_file(input_path)
                if not valid:
                    self.write_error_log(f"Bỏ qua {input_path}: {err_msg}")
                    self.after(0, self.set_file_status, input_path, STATUS_SKIPPED)
                    continue

                self.after(0, self.set_file_status, input_path, STATUS_COMPRESSING)
                self.output_file = self.make_output_path(input_path)
                ok = self.compress_one(input_path, self.output_file, opts, index, total, prefix)
                if self.is_cancelled:
                    self._cleanup_partial_output()
                    break
                if ok:
                    success_count += 1
                    try:
                        in_size = os.path.getsize(input_path)
                        out_size = os.path.getsize(self.output_file)
                        total_in_bytes += in_size
                        total_out_bytes += out_size
                        self.after(0, self.set_file_result, input_path, in_size, out_size)
                    except OSError:
                        pass
                    self.after(0, self.set_file_status, input_path, STATUS_DONE)
                else:
                    self.after(0, self.set_file_status, input_path, STATUS_FAILED)

            savings = self.savings_text(total_in_bytes, total_out_bytes)
            if self.is_cancelled:
                self.after(0, self.finish_compression, self.t("cancelled"), "gray")
            elif success_count == total:
                msg = self.t("done_all", ok=success_count, total=total, savings=savings)
                self.after(0, self.finish_compression, msg, "green", True)
            elif success_count > 0:
                msg = self.t("partial", ok=success_count, total=total, savings=savings)
                self.after(0, self.finish_compression, msg, "orange", True)
            else:
                self.after(0, self.finish_compression, self.t("none_done"), "red")

        except Exception as e:
            self.after(0, self.finish_compression, self.t("sys_error", err=str(e)), "red")
        finally:
            self.process = None

    def savings_text(self, in_bytes, out_bytes):
        """Chuỗi tóm tắt tổng dung lượng tiết kiệm (đã dịch). Rỗng nếu không hợp lệ."""
        if in_bytes <= 0:
            return ""
        in_mb = in_bytes / (1024 * 1024)
        out_mb = out_bytes / (1024 * 1024)
        pct = (1 - out_bytes / in_bytes) * 100
        return self.t("savings", in_mb=in_mb, out_mb=out_mb, pct=pct)

    @staticmethod
    def format_savings(in_bytes, out_bytes):
        """Tóm tắt tổng dung lượng tiết kiệm (uỷ thác cho hàm module).
        Giữ lại cho tương thích; UI dùng savings_text() có dịch."""
        return format_savings(in_bytes, out_bytes)

    def _run_ffmpeg(self, command, total_duration, map_fraction, label):
        """Chạy một tiến trình FFmpeg, cập nhật tiến trình realtime.

        `map_fraction(file_fraction)` đổi % của lượt hiện tại thành % tổng của
        cả lô. Trả về (returncode, stderr_text)."""
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        self.process = process

        # Đọc stderr song song để tránh deadlock do buffer đầy (libx265/x264 ghi nhiều)
        stderr_lines = []

        def drain_stderr():
            for err_line in process.stderr:
                stderr_lines.append(err_line)

        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stderr_thread.start()

        for line in process.stdout:
            file_fraction = parse_progress_fraction(line, total_duration)
            if file_fraction is not None:
                self.after(0, self.update_progress, map_fraction(file_fraction), label)

        process.wait()
        stderr_thread.join(timeout=5)
        return process.returncode, ''.join(stderr_lines)

    def compress_one(self, input_path, output_path, opts, index, total, prefix):
        """Nén một file theo chế độ trong `opts`. Trả về True nếu thành công."""
        total_duration = self.get_video_duration(input_path)
        vcodec = opts["vcodec"]
        preset = opts["preset"]
        force_720p = opts["force_720p"]
        ss = opts.get("ss")
        to = opts.get("to")
        audio = opts.get("audio", "128k")

        # Thời lượng hiệu dụng (sau khi cắt) để tính % tiến trình và bitrate
        eff_duration = total_duration
        if ss or to:
            from_s = parse_time_to_seconds(ss) or 0.0
            to_s = parse_time_to_seconds(to)
            if to_s is not None:
                eff_duration = max(0.1, to_s - from_s)

        if opts["mode"] == MODE_SIZE:
            return self._compress_target_size(
                input_path, output_path, eff_duration, vcodec, preset,
                force_720p, opts["target_mb"], ss, to, audio, index, total, prefix
            )

        # ----- Chế độ CRF (một lượt) -----
        command = build_ffmpeg_command(
            input_path, output_path, opts["crf"], vcodec, force_720p, preset,
            ss=ss, to=to, audio_bitrate=audio
        )
        label = f"{prefix} {self.t('compressing')}"
        rc, stderr_text = self._run_ffmpeg(
            command, eff_duration, lambda f: (index + f) / total, label
        )
        if self.is_cancelled:
            return False
        if rc == 0:
            self.after(0, self.update_progress, (index + 1) / total, label)
            return True
        self.write_error_log(stderr_text)
        return False

    def _compress_target_size(self, input_path, output_path, eff_duration, vcodec,
                              preset, force_720p, target_mb, ss, to, audio, index, total, prefix):
        """Nén để đạt dung lượng mục tiêu (target_mb).
        CPU: 2-pass dùng log; GPU/NVENC: một lượt theo bitrate trung bình."""
        audio_kbps = 128 if audio == "copy" else int(audio.rstrip("k") or 128)
        bitrate = compute_video_bitrate(target_mb, eff_duration, audio_kbps=audio_kbps)
        if bitrate is None:
            self.write_error_log(
                f"Không nén theo dung lượng được cho {input_path}: "
                f"thiếu độ dài video hoặc mục tiêu {target_mb}MB quá nhỏ."
            )
            return False

        # ----- Encoder GPU: một lượt ABR (NVENC không hỗ trợ 2-pass kiểu log) -----
        if is_hardware_encoder(vcodec):
            cmd = build_nvenc_abr_command(
                input_path, output_path, vcodec, bitrate, force_720p, preset,
                ss=ss, to=to, audio_bitrate=audio
            )
            label = f"{prefix} {self.t('compressing_gpu')}"
            rc, err = self._run_ffmpeg(cmd, eff_duration, lambda f: (index + f) / total, label)
            if self.is_cancelled:
                return False
            if rc == 0:
                self.after(0, self.update_progress, (index + 1) / total, f"{prefix} {self.t('file_done')}")
                return True
            self.write_error_log(err)
            return False

        # ----- Encoder CPU: 2-pass -----
        passlog = os.path.join(tempfile.gettempdir(), f"svc_pass_{os.getpid()}_{index}")
        try:
            cmd1, cmd2 = build_two_pass_commands(
                input_path, output_path, vcodec, bitrate, force_720p, preset, passlog,
                ss=ss, to=to, audio_bitrate=audio
            )
            rc1, err1 = self._run_ffmpeg(
                cmd1, eff_duration,
                lambda f: (index + f * 0.5) / total, f"{prefix} {self.t('pass1')}"
            )
            if self.is_cancelled:
                return False
            if rc1 != 0:
                self.write_error_log(err1)
                return False

            rc2, err2 = self._run_ffmpeg(
                cmd2, eff_duration,
                lambda f: (index + 0.5 + f * 0.5) / total, f"{prefix} {self.t('pass2')}"
            )
            if self.is_cancelled:
                return False
            if rc2 == 0:
                self.after(0, self.update_progress, (index + 1) / total, f"{prefix} {self.t('file_done')}")
                return True
            self.write_error_log(err2)
            return False
        finally:
            for leftover in glob.glob(passlog + "*"):
                try:
                    os.remove(leftover)
                except OSError:
                    pass

    def _cleanup_partial_output(self):
        """Xóa file đầu ra dở dang sau khi hủy."""
        try:
            if self.output_file and os.path.exists(self.output_file):
                os.remove(self.output_file)
        except Exception:
            pass

    def finish_compression(self, status_text, text_color, open_output=False):
        self.progress_bar.stop()
        self.progress_bar.set(0 if text_color == "gray" else 1)
        # Khôi phục trạng thái các nút
        self.btn_start.configure(state="normal", text=self.t("btn_start"))
        self.btn_cancel.configure(state="disabled", text=self.t("btn_cancel"))
        self.btn_select.configure(state="normal")
        self.codec_selector.configure(state="normal")
        self.preset_selector.configure(state="normal")
        self.mode_selector.configure(state="normal")
        self.lbl_status.configure(text=status_text, text_color=text_color)

        self.is_cancelled = False
        self.is_running = False
        # Khôi phục trạng thái slider/ô nhập theo chế độ hiện tại
        self._apply_mode_state()

        # Mở thư mục chứa file khi có ít nhất 1 file thành công
        if open_output:
            if self.output_dir and os.path.isdir(self.output_dir):
                self.open_folder(self.output_dir)
            elif self.input_files:
                self.open_folder(os.path.dirname(self.input_files[0]))


if __name__ == "__main__":
    app = VideoCompressorApp()
    app.mainloop()
