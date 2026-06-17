import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import json
import time
import subprocess
import threading
import static_ffmpeg

# Tạo biến môi trường chứa ffmpeg (Nếu máy chưa cài ffmpeg thì cái này tự xử lý)
static_ffmpeg.add_paths()

# Cài đặt giao diện chung
ctk.set_appearance_mode("Dark")  # Giao diện Dark mode xịn xò
ctk.set_default_color_theme("blue")  # Màu chủ đạo là xanh dương

# Bản đồ codec: tên hiển thị -> tham số FFmpeg
CODECS = {
    "H.265 (nén sâu)": "libx265",
    "H.264 (tương thích rộng)": "libx264",
}

# Nơi lưu cấu hình (cạnh file script để dễ tìm)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# Màu trạng thái từng file
STATUS_COLORS = {
    "chờ": "gray",
    "đang nén": "orange",
    "xong": "#3ba55d",
    "lỗi": "#e02f2f",
    "bỏ qua": "#e0a82f",
}


# ---------- Hàm logic thuần (tách riêng để dễ test, không phụ thuộc GUI) ----------
def make_output_path(input_path, exists=os.path.exists):
    """Tạo đường dẫn đầu ra, tránh ghi đè file đã tồn tại.
    `exists` cho phép thay hàm kiểm tra tồn tại khi test."""
    file_dir, file_name = os.path.split(input_path)
    name, ext = os.path.splitext(file_name)
    candidate = os.path.join(file_dir, f"{name}_da_nen{ext}")
    counter = 1
    while exists(candidate):
        candidate = os.path.join(file_dir, f"{name}_da_nen ({counter}){ext}")
        counter += 1
    return candidate


def format_eta(seconds):
    """Định dạng số giây còn lại thành mm:ss (hoặc h:mm:ss)."""
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


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


class VideoCompressorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Super Video Compressor (Free & Lossless Quality)")
        self.geometry("640x860")
        self.minsize(640, 860)

        # Danh sách file đầu vào (hỗ trợ nén hàng loạt)
        self.input_files = []
        self.output_file = ""   # file đầu ra đang xử lý
        self.row_widgets = {}   # input_path -> {"frame":, "status":} để cập nhật trạng thái

        # Trạng thái tiến trình nén
        self.process = None        # tham chiếu tới tiến trình ffmpeg đang chạy
        self.is_cancelled = False  # cờ đánh dấu người dùng đã bấm Hủy
        self.batch_start_time = 0  # mốc thời gian bắt đầu cả lô (để tính ETA)

        # Đọc cấu hình đã lưu (nếu có)
        self.config = self.load_config()
        self.last_dir = self.config.get("last_dir", "")

        self.build_ui()
        self.apply_config()

        # Lưu cấu hình khi đóng cửa sổ
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Cấu hình ----------
    def load_config(self):
        """Đọc config.json (dùng hàm logic thuần cấp module)."""
        return load_config(CONFIG_PATH)

    def save_config(self):
        """Ghi lựa chọn hiện tại ra config.json để lần sau khỏi chỉnh lại."""
        data = {
            "codec": self.codec_selector.get(),
            "crf": int(self.slider_quality.get()),
            "force_720p": bool(self.check_720p.get()),
            "last_dir": self.last_dir,
        }
        save_config(data, CONFIG_PATH)

    def apply_config(self):
        """Áp các giá trị đã lưu lên widget khi mở app."""
        codec = self.config.get("codec")
        if codec in CODECS:
            self.codec_selector.set(codec)

        crf = self.config.get("crf")
        if isinstance(crf, (int, float)) and 18 <= crf <= 50:
            self.slider_quality.set(int(crf))
            self.update_crf_label(int(crf))

        if self.config.get("force_720p"):
            self.check_720p.select()

    def on_close(self):
        """Lưu cấu hình rồi đóng app."""
        self.save_config()
        self.destroy()

    def build_ui(self):
        # Tiêu đề
        self.lbl_title = ctk.CTkLabel(self, text="⚡ NÉN VIDEO SIÊU TỐC ⚡", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=(18, 6))

        self.lbl_subtitle = ctk.CTkLabel(self, text="Giảm đến 90% dung lượng mà không nhận ra sự khác biệt!", font=("Roboto", 13), text_color="gray")
        self.lbl_subtitle.pack(pady=(0, 12))

        # Khung chọn file
        self.frame_file = ctk.CTkFrame(self)
        self.frame_file.pack(pady=8, padx=20, fill="x")

        self.lbl_file_path = ctk.CTkLabel(self.frame_file, text="Chưa chọn video nào...", width=380, anchor="w")
        self.lbl_file_path.pack(side="left", padx=10, pady=10)

        self.btn_select = ctk.CTkButton(self.frame_file, text="Chọn Video", command=self.select_files, width=110)
        self.btn_select.pack(side="right", padx=10, pady=10)

        # Danh sách file (cuộn được) hiển thị trạng thái từng video
        self.frame_list = ctk.CTkScrollableFrame(self, height=130, label_text="Danh sách video")
        self.frame_list.pack(pady=8, padx=20, fill="x")

        # Chọn codec
        self.frame_codec = ctk.CTkFrame(self)
        self.frame_codec.pack(pady=8, padx=20, fill="x")

        self.lbl_codec = ctk.CTkLabel(self.frame_codec, text="Codec:")
        self.lbl_codec.pack(side="left", padx=10, pady=10)

        self.codec_selector = ctk.CTkSegmentedButton(self.frame_codec, values=list(CODECS.keys()))
        self.codec_selector.set("H.265 (nén sâu)")  # mặc định nén sâu
        self.codec_selector.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        # Mức độ nén (CRF)
        self.frame_quality = ctk.CTkFrame(self)
        self.frame_quality.pack(pady=8, padx=20, fill="x")

        self.lbl_quality = ctk.CTkLabel(self.frame_quality, text="Mức nén (CRF):")
        self.lbl_quality.pack(side="left", padx=10, pady=10)

        self.slider_quality = ctk.CTkSlider(self.frame_quality, from_=18, to=50, number_of_steps=32)
        self.slider_quality.set(28)  # Mặc định
        self.slider_quality.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.lbl_crf_val = ctk.CTkLabel(self.frame_quality, text="28 (Khuyên dùng)")
        self.lbl_crf_val.pack(side="right", padx=10, pady=10)

        self.slider_quality.configure(command=lambda v: self.update_crf_label(v))

        # Tuỳ chọn ép giảm cấu hình
        self.frame_options = ctk.CTkFrame(self)
        self.frame_options.pack(pady=0, padx=20, fill="x")

        self.check_720p = ctk.CTkCheckBox(self.frame_options, text="Ép video về chất lượng HD 720p (Đảm bảo dung lượng sẽ giảm cực sâu)")
        self.check_720p.pack(side="left", padx=10, pady=10)

        # Progress bar (kèm nhãn cho dễ thấy)
        self.lbl_progress = ctk.CTkLabel(self, text="Tiến trình nén:", anchor="w")
        self.lbl_progress.pack(pady=(8, 0), padx=20, fill="x")

        self.progress_bar = ctk.CTkProgressBar(
            self,
            mode="determinate",
            height=20,                 # cao hơn để dễ nhìn
            progress_color="#1f6aa5",  # màu fill rõ ràng
            fg_color="#4a4a4a",        # màu track nền sáng hơn nền Dark
        )
        self.progress_bar.pack(pady=(2, 12), padx=20, fill="x")
        self.progress_bar.set(0)

        # Khung chứa nút Bắt đầu và Hủy
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.pack(pady=8, padx=20, fill="x")

        self.btn_start = ctk.CTkButton(self.frame_actions, text="🚀 BẮT ĐẦU NÉN VIDEO", font=("Roboto", 16, "bold"), height=50, command=self.start_compression)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_cancel = ctk.CTkButton(
            self.frame_actions, text="✖ HỦY", font=("Roboto", 16, "bold"), height=50,
            width=110, fg_color="#a83232", hover_color="#8a2929",
            command=self.cancel_compression, state="disabled"
        )
        self.btn_cancel.pack(side="right", padx=(5, 0))

        # Trạng thái
        self.lbl_status = ctk.CTkLabel(self, text="", text_color="green", font=("Roboto", 14), wraplength=600)
        self.lbl_status.pack(pady=(8, 16))

    def update_crf_label(self, value):
        value = int(float(value))
        if value < 23:
            txt = f"{value} (Dung lượng lớn)"
        elif value > 35:
            txt = f"{value} (Ép nén mạnh)"
        else:
            txt = f"{value} (Khuyên dùng)"
        self.lbl_crf_val.configure(text=txt)

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

            lbl_status = ctk.CTkLabel(row, text="● chờ", width=90, anchor="e", text_color=STATUS_COLORS["chờ"])
            lbl_status.pack(side="right", padx=8, pady=4)

            self.row_widgets[path] = {"frame": row, "status": lbl_status}

    def set_file_status(self, path, status):
        """Cập nhật nhãn trạng thái của một file (gọi an toàn từ luồng chính)."""
        widget = self.row_widgets.get(path)
        if widget:
            widget["status"].configure(
                text=f"● {status}",
                text_color=STATUS_COLORS.get(status, "gray")
            )

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
            self.input_files = list(filenames)
            self.last_dir = os.path.dirname(self.input_files[0])
            if len(self.input_files) == 1:
                self.lbl_file_path.configure(text=os.path.basename(self.input_files[0]))
            else:
                self.lbl_file_path.configure(text=f"Đã chọn {len(self.input_files)} video")
            self.rebuild_file_list()
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if 'video' not in result.stdout.decode('utf-8', errors='ignore'):
                return False, "Không chứa luồng video hợp lệ (có thể hỏng/sai định dạng)."
        except FileNotFoundError:
            return False, "Không tìm thấy ffprobe để kiểm tra file."
        return True, ""

    # ---------- Bắt đầu nén ----------
    def start_compression(self):
        if not self.input_files:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn video trước khi nén!")
            return

        # Lưu cấu hình ngay khi bắt đầu (nhớ lựa chọn cho lần sau)
        self.save_config()

        # Reset cờ hủy + mốc thời gian cho lô mới
        self.is_cancelled = False
        self.batch_start_time = time.time()

        # Đặt lại trạng thái mọi file về 'chờ'
        for path in self.input_files:
            self.set_file_status(path, "chờ")

        # Khóa các nút điều khiển, bật nút Hủy
        self.btn_start.configure(state="disabled", text="Đang xử lý, vui lòng chờ...")
        self.btn_select.configure(state="disabled")
        self.codec_selector.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Đang chuẩn bị...", text_color="orange")

        crf_value = int(self.slider_quality.get())
        vcodec = CODECS.get(self.codec_selector.get(), "libx265")
        force_720p = self.check_720p.get() == 1

        threading.Thread(
            target=self.run_batch,
            args=(list(self.input_files), crf_value, vcodec, force_720p),
            daemon=True
        ).start()

    def cancel_compression(self):
        """Hủy tiến trình nén đang chạy (dừng luôn cả lô)."""
        self.is_cancelled = True
        self.btn_cancel.configure(state="disabled", text="Đang hủy...")
        self.lbl_status.configure(text="Đang hủy nén...", text_color="gray")
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.decode('utf-8').strip())
        except (ValueError, FileNotFoundError):
            return 0.0

    @staticmethod
    def format_eta(seconds):
        """Định dạng số giây còn lại (uỷ thác cho hàm module)."""
        return format_eta(seconds)

    def make_output_path(self, input_path):
        """Tạo đường dẫn đầu ra, tránh ghi đè (uỷ thác cho hàm module)."""
        return make_output_path(input_path)

    def update_progress(self, overall_fraction, label_prefix):
        """Cập nhật thanh tiến trình tổng + nhãn % kèm ETA, an toàn từ luồng chính."""
        overall_fraction = max(0.0, min(overall_fraction, 1.0))
        self.progress_bar.set(overall_fraction)

        eta_text = ""
        elapsed = time.time() - self.batch_start_time
        if overall_fraction > 0.01 and elapsed > 1:
            total_est = elapsed / overall_fraction
            remaining = total_est - elapsed
            eta_text = f" • Còn lại ~{self.format_eta(remaining)}"

        self.lbl_status.configure(
            text=f"{label_prefix} {int(overall_fraction * 100)}%{eta_text}",
            text_color="orange"
        )

    # ---------- Vòng nén hàng loạt ----------
    def run_batch(self, files, crf_value, vcodec, force_720p):
        total = len(files)
        success_count = 0
        try:
            for index, input_path in enumerate(files):
                if self.is_cancelled:
                    break

                prefix = f"[{index + 1}/{total}]" if total > 1 else ""

                # Kiểm tra từng file, file lỗi thì bỏ qua và đi tiếp
                valid, err_msg = self.validate_input_file(input_path)
                if not valid:
                    self.write_error_log(f"Bỏ qua {input_path}: {err_msg}")
                    self.after(0, self.set_file_status, input_path, "bỏ qua")
                    continue

                self.after(0, self.set_file_status, input_path, "đang nén")
                self.output_file = self.make_output_path(input_path)
                ok = self.compress_one(
                    input_path, self.output_file, crf_value, vcodec, force_720p,
                    index, total, prefix
                )
                if self.is_cancelled:
                    self._cleanup_partial_output()
                    break
                if ok:
                    success_count += 1
                    self.after(0, self.set_file_status, input_path, "xong")
                else:
                    self.after(0, self.set_file_status, input_path, "lỗi")

            # Tổng kết
            if self.is_cancelled:
                self.after(0, self.finish_compression, "⏹ Đã hủy nén video.", "gray")
            elif success_count == total:
                msg = f"✅ XONG! Đã nén {success_count}/{total} video."
                self.after(0, self.finish_compression, msg, "green")
            elif success_count > 0:
                msg = f"⚠ Hoàn tất: {success_count}/{total} video thành công, phần còn lại bị lỗi (xem log)."
                self.after(0, self.finish_compression, msg, "orange")
            else:
                self.after(0, self.finish_compression, "❌ Không nén được video nào (xem log).", "red")

        except Exception as e:
            self.after(0, self.finish_compression, f"❌ Lỗi do hệ thống: {str(e)}", "red")
        finally:
            self.process = None

    def compress_one(self, input_path, output_path, crf_value, vcodec, force_720p, index, total, prefix):
        """Nén một file. Trả về True nếu thành công."""
        total_duration = self.get_video_duration(input_path)

        command = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-vcodec', vcodec,
            '-crf', str(crf_value),
            '-preset', 'fast',
        ]
        if force_720p:
            command.extend(['-vf', 'scale=-2:720'])
        command.extend([
            '-acodec', 'aac',
            '-progress', 'pipe:1',
            '-nostats',
            output_path
        ])

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        self.process = process

        # Đọc stderr song song để tránh deadlock do buffer đầy (libx265/libx264 ghi nhiều)
        stderr_lines = []

        def drain_stderr():
            for err_line in process.stderr:
                stderr_lines.append(err_line)

        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stderr_thread.start()

        for line in process.stdout:
            line = line.strip()
            if line.startswith('out_time_ms=') and total_duration > 0:
                try:
                    out_time_ms = int(line.split('=', 1)[1])
                    file_fraction = (out_time_ms / 1_000_000) / total_duration
                    file_fraction = max(0.0, min(file_fraction, 1.0))
                    # Tiến trình tổng = số file xong + phần file hiện tại, chia tổng số file
                    overall = (index + file_fraction) / total
                    self.after(0, self.update_progress, overall, f"{prefix} Đang nén...")
                except ValueError:
                    pass

        process.wait()
        stderr_thread.join(timeout=5)

        if self.is_cancelled:
            return False
        if process.returncode == 0:
            # Cập nhật tiến trình tổng cho trọn file này
            self.after(0, self.update_progress, (index + 1) / total, f"{prefix} Đang nén...")
            return True
        else:
            self.write_error_log(''.join(stderr_lines))
            return False

    def _cleanup_partial_output(self):
        """Xóa file đầu ra dở dang sau khi hủy."""
        try:
            if self.output_file and os.path.exists(self.output_file):
                os.remove(self.output_file)
        except Exception:
            pass

    def finish_compression(self, status_text, text_color):
        self.progress_bar.stop()
        self.progress_bar.set(0 if "hủy" in status_text.lower() else 1)
        # Khôi phục trạng thái các nút
        self.btn_start.configure(state="normal", text="🚀 BẮT ĐẦU NÉN VIDEO")
        self.btn_cancel.configure(state="disabled", text="✖ HỦY")
        self.btn_select.configure(state="normal")
        self.codec_selector.configure(state="normal")
        self.lbl_status.configure(text=status_text, text_color=text_color)

        self.is_cancelled = False

        # Mở thư mục chứa file khi có ít nhất 1 file thành công
        if "XONG" in status_text or "Hoàn tất" in status_text:
            if self.input_files:
                self.open_folder(os.path.dirname(self.input_files[0]))


if __name__ == "__main__":
    app = VideoCompressorApp()
    app.mainloop()
