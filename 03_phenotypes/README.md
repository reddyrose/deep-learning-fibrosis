# 03_phenotypes

Phenotype-processing pipeline between the raw U-Net/CVAE percentile outputs (`01_imaging/`, `02_vae/`) and the disease-association/GWAS/PWAS analyses downstream: quality control, hematocrit regression, disease-status annotation, sample/ID mapping, and covariate-table preparation.

## Files, in the order you'd use them

### 1. `01_hematocrit_regression.py`
Quality-controls every subject's myocardium mask (the same donut-contour rule as `01_imaging/unet_quality_control.py`), then regresses hematocrit — and separately, hematocrit + hypertension status — out of the nine T1 distribution metrics.
- **Output:** `cleaned_T1_percentiles.csv`, `cleaned_T1_percentiles_HHregressed.csv` (both under `SHMOLLI-output-unet-myocardium-update2/`) — the latter is read by `04_pwas/` and residualized further by `05_gwas/outliers_residuals_norm.ProblemPhenotypes.R`.
- **Run:** `python 01_hematocrit_regression.py` (edit `BASE_DIR` first).

### 2. `02_ancestry_and_id_mapping.py`
Remaps UK Biobank application-22282 patient IDs to application-24983 IDs (the ID space the imputed genotype files use) for the T1 phenotype residuals and the European-ancestry sample list.
- **Output:** `T1_phenotypes_imputed.no_outliers.residuals.qnorm.txt`, and `euro_minus_exclusion_minus_firstdegree_imputed.txt` — this second file is the `--keep` sample list read directly by `05_gwas/gwas_final_imputed.sh` and `05_gwas/gwas_VAE.sh`.
- **Run:** `python 02_ancestry_and_id_mapping.py`.

### 3. `03_disease_status_annotation.py`
Builds ICD-10-derived disease patient-ID lists (HCM, DCM, valvular disease, amyloidosis, restrictive cardiomyopathy, ischemic/non-ischemic heart disease) and annotates every subject's myocardium/septum row with a status column per disease.
- **Output:** `mean_T1.csv` (myocardium and septum, disease-status columns added), `cleaned_mean_T1_allpheno.csv` (myocardium and septum), and `disease_patient_IDs.txt` — read downstream by `04_pwas/03_PheWAS_delta_rank_test_T1_descriptive_statistics.ipynb` and `08_clinical_associations/02_mortality_curves_chi_squared.ipynb` for the HCM, Valvular, Amyloidosis, Ischemic, and Non-Ischemic disease groups (`cardiac_ids_dict` in those notebooks).
- **Run:** `python 03_disease_status_annotation.py`.

### 4. `04_covariate_prep.py`
Prepares per-phenotype-group covariate tables (VAE latent dimensions, plus one per disease group from step 3) for downstream regression, and remaps a few residual-phenotype files to application-24983 IDs.
- **Run:** `python 04_covariate_prep.py` (after step 3 has produced `mean_T1.csv`, and step 2 has produced the ID-mapping table).

### 5. `05_myocardium_vs_septum_validation.py`
Validation check comparing the whole-myocardium T1 approach used in this pipeline against septal-only T1 — Bland-Altman agreement, correlation, a t-test, and a broader Spearman/Pearson screen against every raw T1 percentile and VAE latent dimension.
- **Run:** `python 05_myocardium_vs_septum_validation.py` (after steps 1 and 3).

## Also in this folder

- **`T1_percentiles_erroded.py` / `.sh`** — an erosion-depth mask-boundary sensitivity analysis.
- **`cardiomyopathy_clustering_exploratory.ipynb`** — unsupervised K-means clustering of LV phenotypes (PCA on LVEF/LVM/LVESV/strain) to derive cardiomyopathy subgroups for a GWAS sensitivity analysis, as an alternative to the ICD-10-based disease groups in `03_disease_status_annotation.py`.
