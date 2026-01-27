# Chess Pix2Pix — Reproducible Submission

This repository contains the full pipeline to:
1) generate synthetic chess renders from FEN labels,
2) build paired synthetic/real datasets, and
3) train + run inference using the provided Colab notebook.

## Repository Layout
```
colab_files/Chess_Project3_Colab.ipynb
generation_files/
  generate_full_generation_without_hands.py
  build_pairs_unzoomed_without_hands.py
  Project2_3 2/
    chess-set.blend
    chess_position_api_angled.py
  Project 1,2,3 - Labeled Chess data (PGN games will be added later)-20251227/
    game*_per_frame/
```

## Environment Setup
### Local (for data generation)
```bash
pip install -r requirements.txt
```

Install Blender separately:
- macOS default path expected by the script:
  - `/Applications/Blender.app/Contents/MacOS/Blender`
- If Blender is elsewhere, edit `BLENDER_APP` inside:
  - `generation_files/generate_full_generation_without_hands.py`

### Colab (for training/inference)
- Open `colab_files/Chess_Project3_Colab.ipynb` in Colab.
- Colab already includes PyTorch. You only need to upload the dataset zip to Drive and update paths in the notebook config section.

## Data Generation (Synthetic Renders)
Run from the repo root:
```bash
python3 "generation_files/generate_full_generation_without_hands.py"
```
This uses:
- FEN labels from `generation_files/Project 1,2,3 - Labeled Chess data (PGN games will be added later)-20251227/`
- Blender project at `generation_files/Project2_3 2/`

Output:
- `generation_files/full_generation_without_hands/`

Optional: restrict games
```bash
python3 "generation_files/generate_full_generation_without_hands.py" --games 2,4,5
```

## Build Paired Dataset (Synthetic A / Real B)
```bash
python3 "generation_files/build_pairs_unzoomed_without_hands.py"
```
Output:
- `generation_files/pairs_unzoomed_without_hands/`
  - `train/A`, `train/B`, `val/A`, `val/B`

## Prepare Dataset Zip for Colab
The notebook expects a zip on Google Drive. Create it from the generated folder:
```bash
cd "generation_files"
zip -r pairs_unzoomed_without_hands_fixedsize.zip pairs_unzoomed_without_hands
```
Upload the zip to Drive and update `ZIP_PATH` in the notebook, or change the notebook config to match your zip name.

## Training (Colab)
1) Open `colab_files/Chess_Project3_Colab.ipynb` in Colab.
2) Set these variables in the **CONFIG** cell:
   - `ZIP_PATH`
   - `DATASET_FOLDER_NAME`
   - `RUNS_BASE_DIR`
3) Run all cells top to bottom.

Checkpoints, samples, and logs are saved to `RUNS_BASE_DIR/RUN_NAME/` in Drive.

## Inference / Evaluation
Inside the notebook:
- The **Inference** section loads the best generator from:
  - `best_generator.pth` (under the run checkpoint folder)
- Place test inputs in `TEST_DIR` (configured in the notebook)
- The notebook outputs generated images and grids into the `tests/` folder of the run.

## Notes
- Data generation uses Blender + `bpy`; this runs inside Blender and is invoked by `generate_full_generation_without_hands.py`.
- The dataset folder and Blender project are located **inside** `generation_files` to match the script’s paths.
- If you change any paths, update the constants at the top of the scripts accordingly.
- Pretrained weights are not included; run training to produce `best_generator.pth`.
