"""Generate SortMeOut app icon."""

from PIL import Image, ImageDraw, ImageFont
import os
import subprocess

RESOURCES = os.path.join(os.path.dirname(__file__), "sortmeout", "resources")
os.makedirs(RESOURCES, exist_ok=True)

size = 1024
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

margin = 80
r = 180
draw.rounded_rectangle(
    [margin, margin, size - margin, size - margin], radius=r, fill=(123, 58, 237)
)
draw.rounded_rectangle(
    [margin + 20, margin + 20, size - margin - 20, size - margin - 20],
    radius=r - 10,
    fill=(139, 92, 246),
)

try:
    font = ImageFont.truetype("/System/Library/Fonts/SFProDisplay-Bold.otf", 500)
except Exception:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 500)
    except Exception:
        font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), "S", font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = (size - tw) / 2 - bbox[0]
ty = (size - th) / 2 - bbox[1] - 20
draw.text((tx, ty), "S", fill=(255, 255, 255), font=font)

png_1024 = os.path.join(RESOURCES, "icon_1024.png")
img.save(png_1024)
print(f"Saved {png_1024}")

for s in [512, 256, 128, 64, 32, 16]:
    resized = img.resize((s, s), Image.Resampling.LANCZOS)
    resized.save(os.path.join(RESOURCES, f"icon_{s}.png"))

print("All icon PNGs generated")

# Build .icns using macOS iconutil
iconset = os.path.join(RESOURCES, "SortMeOut.iconset")
os.makedirs(iconset, exist_ok=True)

icon_sizes = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]

for px, name in icon_sizes:
    resized = img.resize((px, px), Image.Resampling.LANCZOS)
    resized.save(os.path.join(iconset, name))

icns_path = os.path.join(RESOURCES, "SortMeOut.icns")
subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns_path], check=True)
print(f"Created {icns_path}")

# Cleanup iconset
import shutil

shutil.rmtree(iconset)
print("Done!")
