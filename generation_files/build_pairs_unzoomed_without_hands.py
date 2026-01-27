import argparse
import os
import random
import shutil


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RENDERS_DIR = os.path.join(CURRENT_DIR, "full_generation_without_hands")
DATASET_ROOT = os.path.join(
    CURRENT_DIR,
    "Project 1,2,3 - Labeled Chess data (PGN games will be added later)-20251227",
)
OUTPUT_ROOT = os.path.join(CURRENT_DIR, "pairs_unzoomed_without_hands")


def parse_game_frame(filename):
    base = os.path.splitext(filename)[0]
    parts = base.split("_")
    if len(parts) != 3:
        return None, None
    if parts[0] != "game":
        return None, None
    try:
        game_id = int(parts[1])
        frame_id = int(parts[2])
    except ValueError:
        return None, None
    return game_id, frame_id


def build_real_path(game_id, frame_id):
    game_dir = f"game{game_id}_per_frame"
    tagged_dir = os.path.join(DATASET_ROOT, game_dir, "tagged_images")
    frame_name = f"frame_{frame_id:06d}.jpg"
    return os.path.join(tagged_dir, frame_name)


def ensure_dir(path, overwrite=False):
    if overwrite and os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(RENDERS_DIR):
        print(f"Error: renders folder not found at {RENDERS_DIR}")
        return
    if not os.path.exists(DATASET_ROOT):
        print(f"Error: dataset folder not found at {DATASET_ROOT}")
        return

    ensure_dir(OUTPUT_ROOT, overwrite=args.overwrite)
    train_a = os.path.join(OUTPUT_ROOT, "train", "A")
    train_b = os.path.join(OUTPUT_ROOT, "train", "B")
    val_a = os.path.join(OUTPUT_ROOT, "val", "A")
    val_b = os.path.join(OUTPUT_ROOT, "val", "B")
    for p in (train_a, train_b, val_a, val_b):
        ensure_dir(p)

    files = [f for f in os.listdir(RENDERS_DIR) if f.lower().endswith(".png")]
    random.Random(args.seed).shuffle(files)

    split_idx = int(len(files) * args.train_split)
    train_files = set(files[:split_idx])

    copied = 0
    skipped = 0
    skipped_names = []

    for filename in files:
        game_id, frame_id = parse_game_frame(filename)
        if game_id is None:
            skipped += 1
            skipped_names.append(filename)
            continue

        render_path = os.path.join(RENDERS_DIR, filename)
        real_path = build_real_path(game_id, frame_id)
        if not os.path.exists(real_path):
            skipped += 1
            skipped_names.append(filename)
            continue

        is_train = filename in train_files
        out_a = os.path.join(train_a if is_train else val_a, filename)
        out_b = os.path.join(train_b if is_train else val_b, filename)

        shutil.copy2(render_path, out_a)
        shutil.copy2(real_path, out_b)
        copied += 1

    print(f"Done. Copied pairs: {copied}, skipped: {skipped}")
    if skipped_names:
        print("Skipped files:")
        for name in skipped_names:
            print(f"  {name}")
    print(f"Output folder: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
