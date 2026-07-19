# 04_pwas

Proteome-wide association study (PWAS): merges Olink circulating-protein data with the T1/CVAE-latent imaging phenotypes, runs the per-protein regression, and tests for disease associations. Files are numbered by execution order.

## Files, in the order you'd use them

### 1. `01_Protien_GWAS_prep.ipynb`
Assembles phenotype and covariate files needed downstream: merges medication data, disease-status data, and imaging phenotypes; prepares the covariate files consumed by the PWAS regression and by `05_gwas/`.

### 2. `02_PWAS_T1_Time.ipynb`
Merges Olink proteomics (`olink_instance_0.*` columns) with T1/CVAE-latent phenotypes and runs the per-protein OLS regression (protein ~ phenotype) with Benjamini-Hochberg FDR correction, producing the PWAS result tables. Generates heatmap visualizations under four filter/threshold options.

### 3. `03_PheWAS_delta_rank_test_T1_descriptive_statistics.ipynb`
Requires `03_phenotypes/03_disease_status_annotation.py` to have already been run: this notebook reads its `disease_patient_IDs.txt` output for the HCM, Valvular, Amyloidosis, Ischemic, and Non-Ischemic disease groups.

Three analyses:
- **Delta-rank disease-association testing** — Mann-Whitney U test of each T1/latent phenotype between disease-group patients (HCM, Amyloidosis, Ischemic, Non-Ischemic, diabetes types, MI, CKD, Hypertension, Sarcoidosis) and the rest, with effect size and a Bonferroni-corrected significance flag (`p < 0.00025`).
- **Latent-dimension hierarchical clustering** — clusters the 16 CVAE latent dimensions and clusters patients by their latent-dimension profile, with dendrograms and a correlation heatmap.
- **T1 descriptive statistics** — computes T1 distribution summary statistics (mean ± SD, skewness, segmentation success rate).

### `biomarker_panel_exploratory.ipynb` (unnumbered)
A protein-biomarker machine-learning analysis: RandomForest/XGBoost regression and classification predicting T1 phenotypes from PWAS-significant proteins, SHAP feature importance, LASSO 10-/5-protein panels benchmarked against NT-proBNP and Troponin as single biomarkers, SMOTE oversampling, and reduced-panel comparisons. Kept for reference, outside the core reproduction sequence.
