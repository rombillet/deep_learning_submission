import argparse
import csv
import os
import subprocess

import cv2

# === Paths ===
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_DIR = os.path.join(
    CURRENT_DIR,
    "Project 1,2,3 - Labeled Chess data (PGN games will be added later)-20251227",
)
BLENDER_APP = "/Applications/Blender.app/Contents/MacOS/Blender"
BLENDER_PROJECT_FOLDER = os.path.join(CURRENT_DIR, "Project2_3 2")
BLEND_FILE = os.path.join(BLENDER_PROJECT_FOLDER, "chess-set.blend")
SCRIPT_FILE = os.path.join(BLENDER_PROJECT_FOLDER, "chess_position_api_angled.py")
OUTPUT_ROOT = os.path.join(CURRENT_DIR, "full_generation_without_hands")

# === Render quality ===
RESOLUTION = 2000
SAMPLES = 128

# === Angle mapping per game ===
GAME_CONFIG = {
    2: "east",
    4: "west",
    5: "east",
    6: "overhead",
    7: "west",
}

# === Crop points fallback ===
# [y_min, y_max, x_min, x_max]
CROP_COORDS = {
    "east": [814, 1195, 1486, 1873],
    "west": [813, 1198, 132, 518],
    "overhead": [815, 1199, 812, 1196],
}

BLACK_LINE_PIXELS = 7


def crop_black_line_by_angle(img, angle, pixels=BLACK_LINE_PIXELS):
    h, w = img.shape[:2]
    if angle == "east":
        side = "left"
    elif angle == "west":
        side = "right"
    else:
        side = "none"

    if side == "none":
        return img
    if w - h != pixels:
        return img
    if side == "left":
        return img[:, pixels:w]
    if side == "right":
        return img[:, 0:w - pixels]
    return img


def crop_and_save(img_path, output_path, angle):
    if not os.path.exists(img_path):
        return False
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return False

    cropped_img = None
    if img.shape[2] >= 4:
        alpha = img[:, :, 3]
        coords = cv2.findNonZero((alpha > 0).astype("uint8"))
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            cropped_img = img[y:y + h, x:x + w]

    if cropped_img is None:
        coords = CROP_COORDS.get(angle)
        if not coords:
            return False
        y1, y2, x1, x2 = coords
        h, w = img.shape[:2]
        y1, x1 = max(0, y1), max(0, x1)
        y2, x2 = min(h, y2), min(w, x2)
        cropped_img = img[y1:y2, x1:x2]

    cropped_img = crop_black_line_by_angle(cropped_img, angle)
    cv2.imwrite(output_path, cropped_img)
    return True


def find_generated_file(renders_dir, angle):
    if angle == "overhead":
        candidates = ["1_overhead.png"]
    elif angle == "east":
        candidates = ["2_east.png", "3_east.png"]
    else:
        candidates = ["3_west.png", "2_west.png"]

    for name in candidates:
        path = os.path.join(renders_dir, name)
        if os.path.exists(path):
            return path
    return None


def iter_csv_rows(csv_path):
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=str, default="", help="Comma-separated game ids")
    parser.add_argument("--default-angle", type=str, default="", choices=["", "east", "west", "overhead"])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(BASE_DATA_DIR):
        print(f"Error: Data folder not found at {BASE_DATA_DIR}")
        return
    if not os.path.exists(BLENDER_APP):
        print(f"Error: Blender app not found at {BLENDER_APP}")
        return

    if args.games:
        games = []
        for token in args.games.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                games.append(int(token))
            except ValueError:
                print(f"Warning: Skipping invalid game id '{token}'")
    else:
        games = sorted(GAME_CONFIG.keys())

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    renders_dir = os.path.join(BLENDER_PROJECT_FOLDER, "renders")
    os.makedirs(renders_dir, exist_ok=True)

    for game_id in games:
        angle = GAME_CONFIG.get(game_id) or args.default_angle
        if not angle:
            print(f"Warning: No angle for game {game_id}; skipping")
            continue

        csv_folder = f"game{game_id}_per_frame"
        csv_file = f"game{game_id}.csv"
        csv_path = os.path.join(BASE_DATA_DIR, csv_folder, csv_file)
        if not os.path.exists(csv_path):
            print(f"Warning: CSV not found for game {game_id} at {csv_path}")
            continue

        print(f"Processing game {game_id} ({angle})")

        for row in iter_csv_rows(csv_path):
            fen = row.get("fen") or row.get("FEN")
            frame_id = row.get("from_frame") or row.get("frame") or row.get("Frame")
            if not fen or frame_id in (None, ""):
                continue

            out_name = f"game_{game_id}_{frame_id}.png"
            out_path = os.path.join(OUTPUT_ROOT, out_name)
            if not args.overwrite and os.path.exists(out_path):
                continue

            cmd = [
                BLENDER_APP,
                BLEND_FILE,
                "--background",
                "--python",
                SCRIPT_FILE,
                "--",
                "--fen",
                str(fen),
                "--resolution",
                str(RESOLUTION),
                "--samples",
                str(SAMPLES),
                "--view",
                "white",
                "--angle",
                angle,
            ]
            result = subprocess.run(cmd)
            if result.returncode != 0:
                print(f"Warning: Blender failed for game {game_id}, frame {frame_id}")
                continue

            generated = find_generated_file(renders_dir, angle)
            if not generated:
                print(f"Warning: Render not found for game {game_id}, frame {frame_id}")
                continue

            if not crop_and_save(generated, out_path, angle):
                print(f"Warning: Failed to crop for game {game_id}, frame {frame_id}")

    print(f"Done. Output folder: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
