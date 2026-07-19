# 01_imaging

DICOM preprocessing, U-Net myocardium segmentation (training and deployment), mask quality control, and an alternate SAM-based segmentation experiment.

## Files, in the order you'd use them

### 1. `png_dicom_transformer.py`
Converts raw UK Biobank ShMOLLI T1-map DICOMs into filtered PNGs. Scans each patient's unzipped DICOM folder for the specific T1-map slice (`T1MAP` in the DICOM description tag, series/instance `0x020,0x0013 == 2`) and writes it out as a PNG.
- **Input:** a zip file of unzipped-per-patient DICOM folders at `./data/shriya/unfiltered-test-ShMOLLI` (set via `BASE_DIR` at the top of the file).
- **Output:** filtered PNGs under `./data/shriya/UKBB_SHMOLLI-pngimages`.
- **Run:** `python png_dicom_transformer.py` (edit `BASE_DIR` first).

### 2. `01_shriya_unet_myocardium.ipynb` / `shriya_unet_myocardium.py`
Trains the U-Net myocardium segmentation model on the PNGs from step 1, using manually-annotated masks. The notebook and the `.py` script contain the same model definition and training loop; the notebook additionally includes bounding-box preprocessing, quality-control postprocessing (probability threshold, largest-contour extraction, concentric-ring QC), and evaluation plots.
- **Input:** `./data/ekchen/Original-images` (images) and the corresponding mask directory (see notebook for exact path).
- **Output:** trained weights at `./data/shriya/myocardium-unet-ethan.weights.h5` (best checkpoint, saved via Keras `ModelCheckpoint`).
- **Run:** `python shriya_unet_myocardium.py`, or run the notebook top to bottom.
- **Note:** `conv2d_block` in both this file and `deploy_unet_segmentation.py` applies its second convolution to `input_tensor` rather than to the first convolution's output -- see `docs/REVIEW_REQUIRED.md`.

### 3. `deploy_unet_segmentation.py`
Deploys the trained U-Net at scale: segments every patient's T1-map PNG, applies postprocessing (probability threshold, largest-connected-component extraction), and computes T1 percentile statistics (mean, SD, 0.25th/1st/25th/50th/75th/99th/99.75th percentile) within the myocardium mask for every patient.
- **Input:** U-Net weights (`-uw`), a directory of PNG images (`-i`), a postprocessing probability threshold (`-t`, e.g. `0.08`).
- **Output (`-o`):** `statistics.txt`, `percentiles_T1.csv` (one row per patient, the percentile columns above), and a directory of saved mask arrays.
- **Run:**
  ```
  python deploy_unet_segmentation.py -t 0.08 -uw <path>/myocardium-unet-256.h5 -i <path>/UKBB_SHMOLLI-pngimages -o <path>/SHMOLLI-output-unet-myocardium
  ```

### 4. `02_septal-myocardial-quality-comparison.ipynb`
Compares septal-only vs. whole-myocardium segmentation masks as a quality-control check on the deployed segmentation. Applies the production QC rule (checking for two concentric ring-shaped contours) to a sample of masks and inspects agreement between the two mask types.

### 5. `unet_quality_control.py`
Post-hoc QC pass over already-deployed mask CSVs: for every mask, checks whether the binary mask forms a "donut" shape (two closed contour loops -- expected for a myocardial ring), and flags each row in the myocardium and septum `mean_T1.csv` output files with a `quality_controlled` boolean.
- **Input:** `./data/shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv`, `./data/shriya/SHMOLLI-output-unet-septum/mean_T1.csv`, and the corresponding `SAM_masks` directory (paths hardcoded at the bottom of the file via `BASE_DIR`).
- **Output:** the same two CSVs, overwritten in place with the added `quality_controlled` column.
- **Run:** `python unet_quality_control.py` (edit `BASE_DIR` first; no CLI arguments).

### `fine_tune_sam_myocardium_autobounding_box.py` / `deploy_fine_tune_sam_myocardium_autobounding_box.sh`
An alternate segmentation approach: fine-tunes Meta's Segment Anything Model (SAM) on the myocardium dataset (via Hugging Face `transformers`/`datasets`, following the MedSAM recipe), using U-Net-derived bounding boxes as SAM's prompt. Not the model used for the manuscript's reported results (see `01_shriya_unet_myocardium.ipynb`/`deploy_unet_segmentation.py` above) -- kept for reference. Requires a Hugging Face access token (`$HF_TOKEN` environment variable -- **do not hardcode it**; a leaked token was found and removed from this file during repository cleanup, see `docs/REVIEW_REQUIRED.md`).
- **Run (via the SLURM wrapper):** `sbatch deploy_fine_tune_sam_myocardium_autobounding_box.sh`, which calls:
  ```
  python fine_tune_sam_myocardium_autobounding_box.py -t "$HF_TOKEN" -uw <path>/myocardium-unet-256.h5 -n <hf-model-name> -i <path>/UKBB_SHMOLLI-pngimages -o <path>/SHMOLLI-output-2
  ```
- **Output:** a fine-tuned SAM model pushed to the given Hugging Face model name, plus `mean_T1.csv`/`statistics.txt`/mask arrays at `-o`, in the same format as `deploy_unet_segmentation.py`.
