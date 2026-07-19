# Deep learning-derived spatial phenotypes and proteome-wide causal inference identify therapeutic targets for cardiac fibrosis

## Overview

Diffuse myocardial fibrosis is a hallmark of many forms of structural heart disease, but it is difficult to measure at scale: the standard readout, native T1 mapping on cardiac MRI, produces a spatial map of relaxation times across the myocardium, and most analyses collapse that map down to a single mean value per subject, discarding most of the spatial and distributional information it contains.

This project derives a richer fibrosis phenotype from the T1 map than the mean alone — one that captures the shape of the T1 distribution and its spatial structure — and uses that phenotype as an instrument for proteome-wide Mendelian randomization to nominate specific circulating proteins as causal contributors to fibrosis, i.e. candidate drug targets.

The pipeline has two halves:

**Phenotyping (imaging → genetics).** Raw DICOM T1 maps from UK Biobank are converted to images, a U-Net is trained to segment the myocardium, and a convolutional variational autoencoder (CVAE) is trained on the segmented myocardium to learn a compact latent representation of its T1 spatial pattern. Both the CVAE's 16 latent dimensions and a set of hand-engineered T1 percentile/distribution statistics are treated as GWAS phenotypes. Heritability (LDSC) and genetic association testing show that these deep-learning-derived phenotypes are heritable and pick up loci that a simple mean T1 value would miss.

**Causal inference (genetics → protein → target).** The same phenotypes are the outcome in a proteome-wide association study (PWAS) against circulating Olink proteomics, and the outcome in two-sample Mendelian randomization using cis-pQTLs as instruments for thousands of circulating proteins, with colocalization (`coloc.abf`) and MR-PRESSO used to guard against confounding by linkage and pleiotropy. Proteins that survive both screens are prioritized as causal candidates, cross-checked against STRING-db protein-protein interaction networks, and replicated in an independent cohort using deCODE Genetics proteomics summary statistics. Clinical relevance is established separately with Kaplan-Meier/Cox survival analysis and chi-squared disease-prevalence testing against the same phenotypes.

## Repository structure

Each folder is numbered in pipeline order and has its own `README.md` describing every file in it: what it is, what it reads and writes, and the command to run it.

| Folder | Stage |
|---|---|
| [`01_imaging/`](01_imaging/README.md) | DICOM → PNG preprocessing, U-Net myocardium segmentation (training + deployment), mask quality control, SAM fine-tuning. |
| [`02_vae/`](02_vae/README.md) | CVAE training and deployment, latent-dimension extraction, reconstruction-quality evaluation, attention mapping. |
| [`03_phenotypes/`](03_phenotypes/README.md) | Phenotype QC, hematocrit regression, disease-status annotation, sample/ID mapping, and covariate-table preparation. |
| [`04_pwas/`](04_pwas/README.md) | Phenotype/covariate preparation, the per-protein OLS regression that produces the PWAS result tables, and delta-rank disease-association testing. |
| [`05_gwas/`](05_gwas/README.md) | Phenotype residualization/quantile-normalization, PLINK2 GWAS, VCF conversion + liftover + SNP-ID standardization, LDSC heritability/genetic correlation. |
| [`06_mr/`](06_mr/README.md) | cis-pQTL extraction, LD clumping, two-sample Mendelian randomization, colocalization (`06_mr/colocalization/`), and MR-PRESSO sensitivity analysis (`06_mr/mr_presso/`). |
| [`07_decode_validation/`](07_decode_validation/README.md) | Format conversion for external MR replication in the deCODE Genetics cohort. |
| [`08_clinical_associations/`](08_clinical_associations/README.md) | Cross-phenotype correlation, Kaplan-Meier/Cox survival analysis, and chi-squared disease-prevalence testing. |
| [`09_figures/`](09_figures/README.md) | Figure generation, pulling together outputs from the burden test, MR, PWAS, colocalization, and survival analyses. Run last. |

Within each folder, files are numbered by execution order, so directory listing order matches run order. `04_pwas/biomarker_panel_exploratory.ipynb` is left unnumbered: a protein-biomarker machine-learning analysis kept for reference, outside the core reproduction sequence. `03_phenotypes/cardiomyopathy_clustering_exploratory.ipynb` is likewise unnumbered.

Not included in this repository: UK Biobank or other participant-level data; genotype files, proteomic measurements, and summary-statistic result sets; model weights beyond the two CVAE `.weights.h5` files kept for reference (git-ignored); scheduler logs; software environments or licensed reference panels.

## Dependencies

### Python
See [`requirements.txt`](requirements.txt). Pinned: **Python 3.9.7**, NumPy 1.22.4, pandas 2.3.2, SciPy 1.7.1, lifelines 0.30.0. Also used, without a pinned version: TensorFlow, PyTorch, scikit-learn, scikit-image, OpenCV, statsmodels, seaborn, XGBoost, SHAP, imbalanced-learn, UMAP, Plotly, Hugging Face `transformers`/`datasets`, MONAI.

### R
See [`packages.R`](packages.R). Pinned: TwoSampleMR 0.6.14, MendelianRandomization 0.10.0, coloc 5.2.3, MRPRESSO 1.0. Also used, without a pinned version: data.table, dplyr, readr, optparse, future.apply, future, purrr, stringr, renv, ggplot2, matrixStats, preprocessCore, RhpcBLASctl. `renv` is only required if `RENV_DIR` is set to activate a project-local renv environment.

### Command-line tools
- **PLINK / PLINK2** — GWAS (`05_gwas/gwas_final_imputed.sh`, `05_gwas/gwas_VAE.sh`) and LD clumping (`06_mr/clumping_shriya.sh`, PLINK 1.90b5.3).
- **LDSC** (`munge_sumstats.py`, `ldsc.py`) — heritability and genetic correlation (`05_gwas/ldsc_h2_SR.py`).
- **bcftools** — version 1.16.
- **htslib** (`bgzip`, `tabix`) — version 1.16, parameterized via `HTSLIB_BIN`.
- **CrossMap** — hg19→hg38 liftover (`05_gwas/full_hg38_converter_pipline.sh`).
- **Ensembl VEP** — SNP ID standardization (`05_gwas/snp-standardization-workflow.sh`), run via a Singularity container.
- **R** — version 4.4.

## Data availability

This project uses UK Biobank data, available to approved researchers under application 22282; UK Biobank data cannot be redistributed and are not included in this repository. deCODE Genetics proteomics summary statistics used for external replication (`07_decode_validation/`) are available via Eldjarn et al., *Nature* 2023.

## Configuring data paths

Each script uses a `BASE_DIR` variable (and, where relevant, `LIB_DIR`/`RENV_DIR`/`UKBB_DIR`/`HTSLIB_BIN`) at the top of the file, or relative paths of the form `./data/...` in the notebooks. Set `BASE_DIR` to the root of your data directory, or place/symlink your data under a `data/` directory at the repository root matching each subfolder's relative references.

## How to reproduce

Run the numbered folders in order, 1 through 9. Each folder's README gives the exact file-by-file sequence and command; the summary below is the pipeline at a glance:

1. **`01_imaging/`** — DICOM → PNG → trained U-Net → deployed segmentation masks and T1 percentile statistics, quality-controlled.
2. **`02_vae/`** — CVAE trained on the segmented myocardium, evaluated, deployed to extract latent dimensions at scale.
3. **`03_phenotypes/`** — Mask QC and hematocrit regression, ID/ancestry mapping, disease-status annotation, per-group covariate preparation, and a myocardium-vs-septum validation check.
4. **`04_pwas/`** — Phenotype/covariate preparation, per-protein OLS regression (PWAS), delta-rank disease-association testing.
5. **`05_gwas/`** — Phenotype residualization/normalization, PLINK2 GWAS, VCF/liftover/SNP-ID pipeline, LDSC.
6. **`06_mr/`** — cis-pQTL extraction, LD clumping, two-sample MR, colocalization, MR-PRESSO.
7. **`07_decode_validation/`** — deCODE summary-statistic conversion for external MR replication.
8. **`08_clinical_associations/`** — Cross-phenotype correlation, survival analysis, disease-prevalence testing.
9. **`09_figures/`** — Figures, run last once everything above has produced its outputs.

STRING-db protein-protein interaction analysis, final protein prioritization, and the deCODE MR-replication comparison were performed using `06_mr/`'s existing scripts against the deCODE-converted inputs, rather than by separate dedicated code.

## Contact

euan@stanford.edu; bgomes@stanford.edu
