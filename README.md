# Super Video Compressor

A fast, lightweight, and user-friendly GUI application built with Python and `CustomTkinter`. It utilizes the sheer power of `FFmpeg` to drastically compress your videos, often reducing file sizes by up to 90% without any noticeable loss in visual quality!

## 🌟 Features

* **Modern GUI:** A sleek Dark Mode interface built using `CustomTkinter`. Simple and responsive.
* **Lossless-like Quality:** Uses the highly efficient H.265 (`libx265`) codec to minimize file size while preserving stunning visual details.
* **Customizable Compression:** Includes an interactive slider to dial in the perfect CRF (Constant Rate Factor) value, giving you total control over the balance between compression strength and output quality (Defaults to a recommended 28).
* **Extreme Compression Mode:** Check the "Force 720p HD" option to rapidly scale down huge 4K or 1080p videos to 720p, achieving unparalleled file size reduction while maintaining the exact aspect ratio.
* **Smart Audio Handling:** Compresses embedded audio utilizing the `AAC` codec to ensure maximum space-saving efficiency.
* **Auto-Portable FFmpeg:** Integrates `static_ffmpeg` to automatically handle downloading and linking the required FFmpeg binaries onto your machine so you don't have to fiddle with System Environment Variables.
* **Fast and Non-Blocking:** Processes the intensive FFmpeg operations in a background thread, preventing the application UI from freezing. It updates you in real-time and opens the output folder immediately upon finish.

## 🚀 Installation & Requirements

Ensure you have **Python 3.8+** installed. 

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tridpt/VideoCompressor.git
   cd VideoCompressor
   ```

2. **Install dependencies:**
   ```bash
   pip install customtkinter static_ffmpeg
   ```

3. **Run the App:**
   ```bash
   python main.py
   ```

## 🎮 How to Use

1. Click **Chọn Video (Select Video)** and browse for the `.mp4`, `.mkv`, or `.avi` file you wish to compress.
2. Select your compression level using the **CRF slider**. A lower value means larger files & better quality, whereas a higher value means stronger compression & slightly degraded quality. 28 is the sweet spot.
3. *Optional:* Select the 720p downscaler if you're compressing massive videos to send via email or Discord.
4. Hit **BẮT ĐẦU NÉN VIDEO (START)** and let the magic happen. The tool will notify you of the original vs new file size upon completion.

## 👨‍💻 Developer Notes

Developed by **Trần Đức Trí**.
Created to solve the hassle of memorizing long FFmpeg command lines for simple video crunching tasks.
