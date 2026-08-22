"""resize_test_images.py — downsize test images so they clear DashScope's
multimodal upload size limit. Run once before compare.py."""

from PIL import Image
import os

SRC_DIR = "test_images"
MAX_DIMENSION = 1024

for filename in os.listdir(SRC_DIR):
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        continue
    path = os.path.join(SRC_DIR, filename)
    img = Image.open(path)

    if max(img.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        img.save(path, quality=85, optimize=True)
        print(f"Resized {filename} to {new_size}")
    else:
        print(f"{filename} already small enough, skipped")