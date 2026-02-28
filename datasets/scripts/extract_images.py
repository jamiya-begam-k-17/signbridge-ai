import cv2
import os

video_folder = "../raw_videos"
image_folder = "../images"

os.makedirs(image_folder, exist_ok=True)

for video in os.listdir(video_folder):
    if not video.endswith(".mp4"):
        continue

    label = video.split("_")[0] if "_" in video else "unknown"
    label_folder = os.path.join(image_folder, label)
    os.makedirs(label_folder, exist_ok=True)

    video_path = os.path.join(video_folder, video)
    cap = cv2.VideoCapture(video_path)

    frame_count = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % 5 == 0:   # take every 5th frame
            img_name = f"{video[:-4]}_{saved}.jpg"
            cv2.imwrite(os.path.join(label_folder, img_name), frame)
            saved += 1

        frame_count += 1

    cap.release()
    print(f"{video} → {saved} images extracted")

print("Done extracting images")