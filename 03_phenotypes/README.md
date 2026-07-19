# 03_phenotypes

T1 percentile/distribution phenotype extraction from eroded masks (a segmentation-robustness sensitivity check), and LV-phenotype clustering used for GWAS subgroup analysis. Phenotype residualization and quantile-normalization -- the step that actually produces the file GWAS reads as `--pheno` -- lives in `05_gwas/`, not here.

## Files

### `T1_percentiles_erroded.py` / `.sh`
Eroded-mask sensitivity check: erodes each myocardium mask by a configurable number of iterations (`cv2.erode`, `itr` parameter) before recomputing T1 percentile statistics, to test whether shrinking the mask boundary changes the phenotype. The script as checked in hardcodes 8 erosion iterations; the pipeline elsewhere references sibling outputs for 2/4/6/10 iterations, most likely produced by re-running this script with `itr` and the output paths edited each time (see the comment block near the top of the file).
- **Note:** this script computes the 99.5th percentile, not the 99.75th percentile used everywhere else in the pipeline (`01_imaging/deploy_unet_segmentation.py`, etc.). Per the repo owner, **the erosion-sensitivity analysis is not part of the manuscript** -- this discrepancy is moot, not a bug to fix.
- **Run:** `python T1_percentiles_erroded.py` (no CLI arguments; edit the hardcoded `itr` value and output paths at the top of the file to reproduce a different iteration depth), or `sbatch T1_percentiles_erroded.sh`.

### `01_SMHOLLI_tranformer_phenotype_associations.ipynb`
Builds ICD10-code-based disease patient-ID lists (diabetes, MI, DCM, sarcoidosis, CKD, hypertension, etc.), merges U-Net and CVAE-latent phenotype data, and produces the `combined_df.to_csv(...)` output that `02_Clustering_CM_Classification.ipynb` reads. Also contains phenotype-vs-clinical-variable association testing. A deprecated block analyzing an unused `transformers_data` variable (manually-curated high/low-LVM patient image review, not used for the manuscript) was removed during cleanup.

### `02_Clustering_CM_Classification.ipynb`
Clusters patients by LV phenotype to derive cardiomyopathy subgroups, used as a GWAS subgroup sensitivity analysis. Reads the `combined_df` CSV written by the notebook above.
