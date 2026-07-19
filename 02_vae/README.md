# 02_vae

Convolutional variational autoencoder (CVAE) training, evaluation, deployment, and attention mapping. Takes the U-Net myocardium masks from `01_imaging/` and learns a compact latent representation of each subject's T1 spatial pattern.

## Files, in the order you'd use them

### 1. `01_CVAE_myocardium_masks.ipynb`
Builds the myocardium-mask training set, defines the `CVAE` model class, and runs the systematic latent-dimension sweep (`latent_dims = [2, 4, 6, 8, 16, 32, 64, 128]`) that identified **16 dimensions** as optimal -- the manuscript's stated latent size. Ends with a real-model deployment pass matching production preprocessing (bounding-box cropping).

### 2. `train_VAE_optimized.py` (canonical) / `train_VAE_optimized_alt.py`
Trains the CVAE. **`train_VAE_optimized.py` is the confirmed-canonical training script** -- its exponential-decay learning-rate schedule (factor 0.9 every 10,000 steps) matches the manuscript exactly. `train_VAE_optimized_alt.py` is an earlier version (`CosineDecay` schedule, different loss-computation structure, no early stopping) kept for reference but not used for reported results.
- **Args:** `-i` image folder (myocardium masks), `-o` output directory, `-qc` a quality-control CSV path, `-b` batch size, `-e` epochs, `-ld` latent dimension count.
- **Output:** `cvae_<ld>d_optimized.weights.h5` and a `training_loss_<ld>d.png` plot, both written to `-o`.
- **Run (via the SLURM wrapper `train_VAE.sh`):**
  ```
  python train_VAE_optimized.py -i <path>/SAM_masks -o <path>/VAE_rerun_trials/run_4 -qc <path>/mean_T1.csv -b 32 -e 200 -ld 16
  ```

### 3. `vae_evaluation.py`
Evaluates a trained CVAE's reconstruction quality (MSE, PSNR, SSIM, Dice) on held-out images, and `02_CVAE_evaluation_cleaned.ipynb` / `02_CVAE_evaluation_Rerun_alt.ipynb` do the same interactively. **Canonicity between the two evaluation notebooks is unresolved** -- both were kept, `_Rerun_alt` suffixed as the less-certain one; see `docs/REVIEW_REQUIRED.md`.
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
Produces Grad-CAM-style attention maps showing which spatial regions of the myocardium mask drive each latent dimension's activation, using a `VAEGradCAM` class built on the trained CVAE. Reordered during repository cleanup to be runnable top to bottom (it originally was not).

## Reference artifacts (not scripts)
- **`cvae_16d_best.weights.h5`, `cvae_16d_optimized.weights.h5`** -- saved model weights, git-ignored (large binary; see repo-root `.gitignore`). Kept locally for reference/reproduction of the exact reported model.
- **`training_loss_16d.png`** -- training-loss curve for the 16-dimensional model, produced by `train_VAE_optimized.py`.
