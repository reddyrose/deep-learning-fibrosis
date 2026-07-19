# 02_vae

Convolutional variational autoencoder (CVAE) training, evaluation, deployment, and attention mapping. Takes the U-Net myocardium masks from `01_imaging/` and learns a compact latent representation of each subject's T1 spatial pattern.

## Files, in the order you'd use them

### 1. `01_CVAE_myocardium_masks.ipynb`
Builds the myocardium-mask training set, defines the `CVAE` model class, and runs a systematic latent-dimension sweep (`latent_dims = [2, 4, 6, 8, 16, 32, 64, 128]`) identifying 16 dimensions as optimal. Ends with a real-model deployment pass matching production preprocessing (bounding-box cropping).

### 2. `train_VAE_optimized.py`
Trains the CVAE with a cosine-decay learning-rate schedule (starting at 1e-3, decaying across `epochs * 1250` steps) and early stopping (patience 10 epochs without validation-ELBO improvement).
- **Args:** `-i` image folder (myocardium masks), `-o` output directory, `-qc` a quality-control CSV path, `-b` batch size, `-e` epochs, `-ld` latent dimension count.
- **Output:** `cvae_<ld>d_best.weights.h5` (saved whenever validation ELBO improves) and a `training_loss_<ld>d.png` plot, both written to `-o`.
- **Run (via the SLURM wrapper `train_VAE.sh`):**
  ```
  python train_VAE_optimized.py -i <path>/SAM_masks -o <path>/VAE_rerun_trials/run_4 -qc <path>/mean_T1.csv -b 32 -e 200 -ld 16
  ```

`train_VAE_optimized_alt.py` is an alternate version with an exponential-decay LR schedule (factor 0.9 every 10,000 steps) and no early stopping, kept for reference.

### 3. `vae_evaluation.py`
Evaluates a trained CVAE's reconstruction quality (MSE, PSNR, SSIM, Dice) on held-out images. `02_CVAE_evaluation_cleaned.ipynb` and `02_CVAE_evaluation_Rerun_alt.ipynb` run the same evaluation interactively.
- **Args:** `-i` image folder, `-o` output directory, `-qc` quality-control CSV, `-m` model weights path, `-b` batch size (default 32), `-ld` latent dimension, `-n` number of sample reconstructions to visualize (default 10).
- **Run:** `python vae_evaluation.py -i <path>/SAM_masks -o <path>/eval_output -qc <path>/mean_T1.csv -m <path>/cvae_16d_best.weights.h5 -ld 16`

### 4. `deploy_VAE_reconstruction.py` / `.sh`
Deploys the trained CVAE at scale: encodes every subject's myocardium mask to its 16 latent dimensions and computes T1 percentile statistics per subject, in the same style as `01_imaging/deploy_unet_segmentation.py`.
- **Args:** `-mw` model weights, `-i` image folder, `-o` output directory, `-d` latent dimension count.
- **Output (`-o`):** `percentiles_T1_latent_spaces.csv` (one row per subject: latent dimensions + T1 percentiles) and a `VAE_masks/` directory of reconstructed prediction images.
- **Run (via the SLURM wrapper):**
  ```
  python deploy_VAE_reconstruction.py -mw <path>/cvae_16d_best.weights.h5 -i <path>/SAM_masks -o <path>/SHMOLLI_VAE_16_output -d 16
  ```

### 5. `03_VAE_Attention_Mapping.ipynb`
Produces Grad-CAM-style attention maps showing which spatial regions of the myocardium mask drive each latent dimension's activation, using a `VAEGradCAM` class built on the trained CVAE.

## Reference artifacts (not scripts)
- **`cvae_16d_best.weights.h5`** — the reported model's saved weights (from `train_VAE_optimized.py`), git-ignored (large binary; see repo-root `.gitignore`).
- **`cvae_16d_optimized.weights.h5`** — weights from `train_VAE_optimized_alt.py`, git-ignored.
- **`training_loss_16d.png`** — training-loss curve for the 16-dimensional model.
