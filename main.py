import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import subprocess
import threading
import static_ffmpeg

# Tạo biến môi trường chứa ffmpeg (Nếu máy chưa cài ffmpeg thì cái này tự xử lý)
static_ffmpeg.add_paths()

# Cài đặt giao diện chung
ctk.set_appearance_mode("Dark")  # Giao diện Dark mode xịn xò
ctk.set_default_color_theme("blue")  # Màu chủ đạo là xanh dương

class VideoCompressorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Super Video Compressor (Free & Lossless Quality)")
        self.geometry("600x450")
        self.resizable(False, False)

        # File path variables
        self.input_file = ""
        self.output_file = ""

        self.build_ui()

    def build_ui(self):
        # Tiêu đề
        self.lbl_title = ctk.CTkLabel(self, text="⚡ NÉN VIDEO SIÊU TỐC ⚡", font=("Roboto", 24, "bold"))
        self.lbl_title.pack(pady=(20, 10))

        self.lbl_subtitle = ctk.CTkLabel(self, text="Giảm đến 90% dung lượng mà không nhận ra sự khác biệt!", font=("Roboto", 13), text_color="gray")
        self.lbl_subtitle.pack(pady=(0, 20))

        # Khung chọn file
        self.frame_file = ctk.CTkFrame(self)
        self.frame_file.pack(pady=10, padx=20, fill="x")

        self.lbl_file_path = ctk.CTkLabel(self.frame_file, text="Chưa chọn video nào...", width=400, anchor="w")
        self.lbl_file_path.pack(side="left", padx=10, pady=10)

        self.btn_select = ctk.CTkButton(self.frame_file, text="Chọn Video", command=self.select_file, width=100)
        self.btn_select.pack(side="right", padx=10, pady=10)

        # Mức độ nén (CRF)
        self.frame_quality = ctk.CTkFrame(self)
        self.frame_quality.pack(pady=10, padx=20, fill="x")

        self.lbl_quality = ctk.CTkLabel(self.frame_quality, text="Mức nén (CRF):")
        self.lbl_quality.pack(side="left", padx=10, pady=10)

        self.slider_quality = ctk.CTkSlider(self.frame_quality, from_=18, to=50, number_of_steps=32)
        self.slider_quality.set(28) # Mặc định
        self.slider_quality.pack(side="left", padx=10, pady=10, expand=True, fill="x")

        self.lbl_crf_val = ctk.CTkLabel(self.frame_quality, text="28 (Khuyên dùng)")
        self.lbl_crf_val.pack(side="right", padx=10, pady=10)

        def update_crf_label(value):
            if value < 23:
                txt = f"{int(value)} (Dung lượng lớn)"
            elif value > 35:
                txt = f"{int(value)} (Ép nén mạnh)"
            else:
                txt = f"{int(value)} (Khuyên dùng)"
            self.lbl_crf_val.configure(text=txt)

        self.slider_quality.configure(command=update_crf_label)

        # Tuỳ chọn ép giảm cấu hình
        self.frame_options = ctk.CTkFrame(self)
        self.frame_options.pack(pady=0, padx=20, fill="x")
        
        self.check_720p = ctk.CTkCheckBox(self.frame_options, text="Ép video về chất lượng HD 720p (Đảm bảo dung lượng sẽ giảm cực sâu)")
        self.check_720p.pack(side="left", padx=10, pady=10)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.pack(pady=20, padx=20, fill="x")
        self.progress_bar.set(0)

        # Nút Bắt đầu
        self.btn_start = ctk.CTkButton(self, text="🚀 BẮT ĐẦU NÉN VIDEO", font=("Roboto", 16, "bold"), height=50, command=self.start_compression)
        self.btn_start.pack(pady=10, padx=20, fill="x")

        # Trạng thái
        self.lbl_status = ctk.CTkLabel(self, text="", text_color="green", font=("Roboto", 14))
        self.lbl_status.pack(pady=10)

    def select_file(self):
        filetypes = (
            ('Video files', '*.mp4 *.mkv *.avi *.mov *.flv'),
            ('All files', '*.*')
        )
        filename = filedialog.askopenfilename(title="Chọn video gốc", filetypes=filetypes)
        if filename:
            self.input_file = filename
            # Cập nhật hiển thị tên file ngắn gọn nếu quá dài
            display_name = os.path.basename(filename)
            self.lbl_file_path.configure(text=display_name)
            self.lbl_status.configure(text="")
            self.progress_bar.stop()
            self.progress_bar.set(0)

    def start_compression(self):
        if not self.input_file:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn video trước khi nén!")
            return

        # Nơi lưu file đầu ra (tránh ghi đè file đã tồn tại)
        file_dir, file_name = os.path.split(self.input_file)
        name, ext = os.path.splitext(file_name)
        candidate = os.path.join(file_dir, f"{name}_da_nen{ext}")
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(file_dir, f"{name}_da_nen ({counter}){ext}")
            counter += 1
        self.output_file = candidate

        # Vô hiệu hóa nút và reset thanh tiến trình về 0
        self.btn_start.configure(state="disabled", text="Đang xử lý, vui lòng chờ...")
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Đang nén video... Máy tính hơi nóng là bình thường nhé!", text_color="orange")

        # Chạy logic nén trong luồng riêng để không bị đơ UI
        crf_value = int(self.slider_quality.get())
        threading.Thread(target=self.run_ffmpeg, args=(crf_value,), daemon=True).start()

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
        """Ghi toàn bộ lỗi FFmpeg ra file log cạnh file gốc để tiện debug."""
        try:
            log_dir = os.path.dirname(self.input_file) or os.getcwd()
            log_path = os.path.join(log_dir, 'video_compressor_error.log')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(error_text)
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

    def update_progress(self, fraction):
        """Cập nhật thanh tiến trình và nhãn % an toàn từ luồng chính."""
        fraction = max(0.0, min(fraction, 1.0))
        self.progress_bar.set(fraction)
        self.lbl_status.configure(
            text=f"Đang nén video... {int(fraction * 100)}%",
            text_color="orange"
        )

    def run_ffmpeg(self, crf_value):
        try:
            # Tổng thời lượng video, dùng để quy ra phần trăm tiến trình
            total_duration = self.get_video_duration(self.input_file)

            # Lệnh FFmpeg siêu mạnh
            command = [
                'ffmpeg',
                '-y', # Ghi đè file nếu đã tồn tại
                '-i', self.input_file,
                '-vcodec', 'libx265', # Chuẩn nén H.265 tối ưu
                '-crf', str(crf_value),
                '-preset', 'fast',
            ]
            
            # Kiểm tra nếu người dùng chọn ép về 720p
            if self.check_720p.get() == 1:
                # Lệnh scale của FFmpeg: đưa chiều cao về 720, chiều rộng tự động nội suy (-2) để giữ đúng tỷ lệ khung hình
                command.extend(['-vf', 'scale=-2:720'])
            
            # Thêm nén âm thanh, xuất tiến trình ra stdout và đường dẫn đầu ra
            command.extend([
                '-acodec', 'aac', # Nén luôn âm thanh
                '-progress', 'pipe:1', # In tiến trình theo máy đọc ra stdout
                '-nostats',
                self.output_file
            ])

            # Mở tiến trình và đọc dần stdout để cập nhật phần trăm
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for line in process.stdout:
                line = line.strip()
                if line.startswith('out_time_ms=') and total_duration > 0:
                    try:
                        out_time_ms = int(line.split('=', 1)[1])
                        fraction = (out_time_ms / 1_000_000) / total_duration
                        self.after(0, self.update_progress, fraction)
                    except ValueError:
                        pass

            # Đợi tiến trình kết thúc và lấy phần stderr còn lại
            stderr_output = process.stderr.read()
            process.wait()

            if process.returncode == 0:
                # Thành công
                size_in = os.path.getsize(self.input_file) / (1024 * 1024)
                size_out = os.path.getsize(self.output_file) / (1024 * 1024)
                
                success_msg = f"✅ XONG! Gốc: {size_in:.2f}MB ➡️ Nén: {size_out:.2f}MB"
                
                # Cập nhật UI an toàn từ luồng phụ vào luồng chính qua phương thức after()
                self.after(0, self.finish_compression, success_msg, "green", "BẮT ĐẦU NÉN VIDEO")
            else:
                # Lỗi - ghi full log ra file, hiển thị gọn trên UI
                log_path = self.write_error_log(stderr_output)
                short_msg = "❌ Lỗi khi nén video."
                if log_path:
                    short_msg += f" Chi tiết đã lưu tại: {os.path.basename(log_path)}"
                self.after(0, self.finish_compression, short_msg, "red", "THỬ LẠI")

        except Exception as e:
            self.after(0, self.finish_compression, f"❌ Lỗi do hệ thống: {str(e)}", "red", "THỬ LẠI")

    def finish_compression(self, status_text, text_color, btn_text):
        self.progress_bar.stop()
        self.progress_bar.set(1) # Full 100%
        self.btn_start.configure(state="normal", text=btn_text)
        self.lbl_status.configure(text=status_text, text_color=text_color)
        
        # Mở thư mục chứa file (đa nền tảng)
        if "XONG" in status_text and hasattr(self, 'output_file'):
            self.open_folder(os.path.dirname(self.output_file))

if __name__ == "__main__":
    app = VideoCompressorApp()
    app.mainloop()
