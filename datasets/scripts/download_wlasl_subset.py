import json
import os
import yt_dlp

# ==== CHANGE YOUR 5 SIGNS HERE ====
selected_signs = ["hello", "help", "water", "yes", "no"]
# selected_signs = ['thank you', 'thanksgiving']
# paths
json_path = "../WLASL_v0.3.json"
output_dir = "../raw_videos"

os.makedirs(output_dir, exist_ok=True)

# load json
with open(json_path, "r") as f:
    data = json.load(f)

# yt downloader settings
ydl_opts = {
    "outtmpl": output_dir + "/%(title)s.%(ext)s",
    "format": "mp4",
    "quiet": True
}

ydl = yt_dlp.YoutubeDL(ydl_opts)

count = 0

for item in data:
    gloss = item["gloss"]

    if gloss.lower() in selected_signs:
        print(f"\nDownloading videos for: {gloss}")

        for inst in item["instances"][:30]:   # max 30 videos per sign
            url = inst["url"]
            try:
                ydl.download([url])
                count += 1
            except:
                print("Failed:", url)

print(f"\nDownloaded {count} videos total")