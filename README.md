🎬 ProStream

ProStream is a modern, high-performance media downloader featuring a stunning Apple-style Glassmorphism UI. Built with Python (Flask) and vanilla JavaScript, it provides studio-quality audio extraction and video downloads without the clutter.

✨ Features

🎨 Premium UI: Beautiful, responsive interface with Tailwind CSS and glassmorphism effects.

🎵 Audio Extraction: High-quality MP3 conversion.

🎥 Video Downloads: Crisp MP4 video downloading.

⚡ Fast Processing: Powered by yt-dlp and FFmpeg for optimal speed.

📜 History Tracking: Local storage-based history of your recent downloads.

🛠️ Installation & Setup

Follow these steps to get ProStream running on your local machine.

1. Clone the Repository

git clone [https://github.com/yourusername/prostream.git](https://github.com/yourusername/prostream.git)
cd prostream


2. Install Python Dependencies

Make sure you have Python installed, then run:

pip install -r requirements.txt


3. ⚙️ FFmpeg Setup (CRITICAL STEP)

To enable media conversion/processing, you must manually set up FFmpeg. Please follow these exact steps:

Download the Build: Click the link below to download the latest shared build for Windows (64-bit):

📥 Download FFmpeg (BtbN Builds) (Source: BtbN/FFmpeg-Builds Releases)

Extract: Unzip the downloaded folder (ffmpeg-master-latest-win64-gpl-shared.zip).

Locate Binaries: Open the extracted folder and navigate into the bin folder. You should see three specific files:

ffmpeg.exe

ffplay.exe

ffprobe.exe

Copy & Paste: Copy all three of those .exe files.

Paste them directly into the root folder of this project (the exact same folder where app.py is located).

⚠️ Note: Your project folder structure should look like this:

prostream/
├── app.py
├── templates/
├── static/
├── ffmpeg.exe  <-- Paste here
├── ffplay.exe  <-- Paste here
└── ffprobe.exe <-- Paste here


🚀 Usage

Once FFmpeg is set up, you can launch the application:

Run the application:

python app.py


Open your browser and navigate to:

[http://127.0.0.1:5000](http://127.0.0.1:5000)


Paste a YouTube link and enjoy!

🤝 Contributing

Contributions are welcome! If you have suggestions for the UI or backend improvements:

Fork the Project

Create your Feature Branch (git checkout -b feature/AmazingFeature)

Commit your Changes (git commit -m 'Add some AmazingFeature')

Push to the Branch (git push origin feature/AmazingFeature)

Open a Pull Request

📄 License

Distributed under the MIT License. See LICENSE for more information.

<p align="center"> Made with ❤️ by HaiCLOP Labs </p>
