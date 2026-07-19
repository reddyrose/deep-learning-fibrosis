# Deep learning-derived spatial phenotypes and proteome-wide causal inference identify therapeutic targets for cardiac fibrosis

## Overview

Diffuse myocardial fibrosis is a hallmark of many forms of structural heart disease, but it's difficult to measure at scale: the gold-standard readout, native T1 mapping on cardiac MRI, produces a spatial map of relaxation times across the myocardium, and most analyses collapse that map down to a single mean value per subject, discarding almost all of the spatial and distributional information it contains.

This project asks two questions. First, can a deep-learning model extract a *richer* fibrosis phenotype from the T1 map than the mean -- one that captures the shape of the T1 distribution and its spatial structure, not just its average -- and does that richer phenotype carry more genetic and clinical signal than the mean does? Second, once you have that phenotype, can you use it as an instrument for proteome-wide Mendelian randomization to nominate specific circulating proteins as *causal* contributors to fibrosis, rather than merely correlated with it -- i.e. candidate drug targets?

The pipeline that answers these questions has two halves:

**Phenotyping (imaging -> genetics).** Raw DICOM T1 maps from UK Biobank are converted to images, a U-Net is trained to segment the myocardium, and a convolutional variational autoencoder (CVAE) is trained on the segmented myocardium to learn a compact latent representation of its T1 spatial pattern. Both the CVAE's 16 latent dimensions and a set of hand-engineered T1 percentile/distribution statistics are treated as GWAS phenotypes. Heritability (LDSC) and genetic association testing establish that these deep-learning-derived phenotypes are heritable and pick up loci that a simple mean T1 value would miss.

**Causal inference (genetics -> protein -> target).** The same phenotypes are the outcome in a proteome-wide association study (PWAS) against circulating Olink proteomics, and the outcome in two-sample Mendelian randomization using cis-pQTLs as instruments for ~thousands of circulating proteins, with colocalization (`coloc.abf`) and MR-PRESSO used to guard against confounding by linkage and pleiotropy. Proteins that survive both screens are prioritized as causal candidates, cross-checked against STRING-db protein-protein interaction networks, and replicated in an independent cohort using deCODE Genetics proteomics summary statistics. Clinical relevance is established separately with Kaplan-Meier/Cox survival analysis and chi-squared disease-prevalence testing against the same phenotypes.

## Repository structure

Each folder below is numbered in pipeline order and has **its own `README.md`** describing every file in it: what it is, what it reads and writes, and the exact command to run it. This top-level README covers the project as a whole; go to a folder's README for file-by-file detail.

| Folder | Stage |
|---|---|
| [`01_imaging/`](01_imaging/README.md) | DICOM -> PNG preprocessing, U-Net myocardium segmentation (training + deployment), mask quality control, SAM fine-tuning experiment. |
| [`02_vae/`](02_vae/README.md) | CVAE training and deployment, latent-dimension extraction, reconstruction-quality evaluation, attention mapping. |
| [`03_phenotypes/`](03_phenotypes/README.md) | T1 percentile/distribution phenotype extraction and LV-phenotype clustering for GWAS subgroup sensitivity analysis. |
| [`04_pwas/`](04_pwas/README.md) | Phenotype/covariate preparation, the per-protein OLS regression that produces the PWAS result tables, and delta-rank disease-association testing. |
| [`05_gwas/`](05_gwas/README.md) | Phenotype residualization/quantile-normalization, PLINK2 GWAS, VCF conversion + liftover + SNP-ID standardization, LDSC heritability/genetic correlation. |
| [`06_mr/`](06_mr/README.md) | cis-pQTL extraction, LD clumping, two-sample Mendelian randomization, colocalization (`06_mr/colocalization/`), and MR-PRESSO sensitivity analysis (`06_mr/mr_presso/`). |
| [`07_decode_validation/`](07_decode_validation/README.md) | Format conversion for external MR replication in the deCODE Genetics cohort. |
| [`08_clinical_associations/`](08_clinical_associations/README.md) | Cross-phenotype correlation (PheWAS-style), Kaplan-Meier/Cox survival analysis, and chi-squared disease-prevalence testing. |
| [`09_figures/`](09_figures/README.md) | Manuscript figure generation, pulling together outputs from the burden test, MR, PWAS, colocalization, and survival analyses. Run last. |
| [`docs/`](docs/) | `MANIFEST.tsv` (every file's size, SHA-256 checksum, and origin), `CHECKS.md` (parseability/hygiene validation results), and `REVIEW_REQUIRED.md` (open questions and manuscript-text notes still to resolve before submission). |

Within each folder, notebooks are numbered by execution order (`01_...`, `02_...`, etc.) rather than alphabetically, so directory listing order matches run order. Notebooks have also been trimmed to the cells that actually feed a saved file, a reported statistic, or a downstream cell -- dead, broken, duplicate, and exploratory-only cells were removed. One notebook, `04_pwas/biomarker_panel_exploratory.ipynb`, is deliberately left unnumbered: it's a protein-biomarker machine-learning analysis that isn't part of the manuscript's reported methods, kept for reference but outside the required reproduction sequence.

Not included in this repository: UK Biobank or other participant-level data; genotype files, proteomic measurements, and summary-statistic result sets; model weights beyond the two CVAE `.weights.h5` files kept for reference (git-ignored, see below); scheduler logs; software environments or licensed reference panels.

## Dependencies

### Python
See [`requirements.txt`](requirements.txt). Versions pinned in the manuscript Methods: **Python 3.9.7**, NumPy 1.22.4, pandas 2.3.2, SciPy 1.7.1, lifelines 0.30.0. All other Python packages (TensorFlow, PyTorch, scikit-learn, scikit-image, OpenCV, statsmodels, seaborn, XGBoost, SHAP, imbalanced-learn, UMAP, Plotly, Hugging Face `transformers`/`datasets`, MONAI, etc.) are used without a version pin in the original code -- **version unspecified, confirm before submission**.

### R
See [`packages.R`](packages.R). Versions pinned in the manuscript Methods: TwoSampleMR 0.6.14, MendelianRandomization 0.10.0, coloc 5.2.3, MRPRESSO 1.0. All other R packages (data.table, dplyr, readr, optparse, future.apply, future, purrr, stringr, renv, ggplot2, matrixStats, preprocessCore, RhpcBLASctl) are used without a version pin -- **version unspecified, confirm before submission**. `renv` is only required if you set `RENV_DIR` to activate a project-local renv environment; several `06_mr/` scripts default to skipping this.

### Command-line tools
- **PLINK / PLINK2** -- GWAS (`05_gwas/gwas_final_imputed.sh`, `05_gwas/gwas_VAE.sh`) and LD clumping (`06_mr/clumping_shriya.sh`, PLINK 1.90b5.3 per `06_mr/clumping_shriya_job.sh`). PLINK2 version unspecified (Sherlock module referenced `plink/2.0a2`) -- confirm before submission.
- **LDSC** (`munge_sumstats.py`, `ldsc.py`) -- heritability and genetic correlation (`05_gwas/ldsc_h2_SR.py`). Version unspecified -- confirm before submission.
- **bcftools** -- version 1.16 (`05_gwas/full_hg38_converter_pipline.sh`, `06_mr/clumping_shriya_job.sh`).
- **htslib** (`bgzip`, `tabix`) -- version 1.16 (parameterized via `HTSLIB_BIN`).
- **CrossMap** -- hg19->hg38 liftover (`05_gwas/full_hg38_converter_pipline.sh`). Version unspecified -- confirm before submission.
- **Ensembl VEP** -- SNP ID standardization (`05_gwas/snp-standardization-workflow.sh`), run via a Singularity container tagged `:latest` (no pinned version) -- confirm before submission and consider pinning a specific VEP release.
- **R** -- version 4.4 (`06_mr/mr_presso/run_MR_PRESSO.sh` references R/4.4.2 specifically).

## Data availability

This project uses UK Biobank data, which requires approved access under **UK Biobank application 22282**; UK Biobank data cannot be redistributed and are not included in this repository. deCODE Genetics proteomics summary statistics used for external replication (`07_decode_validation/`) are available via the original publication: **Eldjarn et al., *Nature* 2023**.

## Configuring data paths

Every script in this repository has had its Sherlock HPC (`/oak/stanford/groups/euan/projects/...`), Google Colab Drive mount (`/content/drive/MyDrive/Shriya/...`), or local-machine absolute paths replaced with either:
- a `BASE_DIR` variable (and, where relevant, `LIB_DIR`/`RENV_DIR`/`UKBB_DIR`/`HTSLIB_BIN`) at the top of the shell/R/Python script -- set it to the root of your own data directory before running, or
- relative paths of the form `./data/...` in the notebooks -- place or symlink your data under a `data/` directory at the repository root, matching each subfolder's relative reference.

No analysis logic was changed -- only path handling.

## How to reproduce

Run the numbered folders in order, 1 through 9. Each folder's own README gives the exact file-by-file sequence and command to run; the summary below is the pipeline at a glance:

1. **`01_imaging/`** -- DICOM -> PNG -> trained U-Net -> deployed segmentation masks + T1 percentile statistics, QC'd.
2. **`02_vae/`** -- CVAE trained on the segmented myocardium, evaluated, deployed to extract latent dimensions at scale.
3. **`03_phenotypes/`** -- Eroded-mask T1 percentiles and LV-phenotype clustering for sensitivity analyses.
4. **`04_pwas/`** -- Phenotype/covariate prep, per-protein OLS regression (PWAS), delta-rank disease-association testing.
5. **`05_gwas/`** -- Phenotype residualization/normalization, PLINK2 GWAS, VCF/liftover/SNP-ID pipeline, LDSC.
6. **`06_mr/`** -- cis-pQTL extraction, LD clumping, two-sample MR, colocalization, MR-PRESSO.
7. **`07_decode_validation/`** -- deCODE summary-statistic conversion for external MR replication.
8. **`08_clinical_associations/`** -- Cross-phenotype correlation, survival analysis, disease-prevalence testing.
9. **`09_figures/`** -- Manuscript figures, run last once everything above has produced its outputs.

STRING-db protein-protein interaction analysis, the final top-candidate protein prioritization, and the deCODE MR-replication comparison itself were performed manually / by reusing `06_mr/`'s existing scripts rather than by dedicated code in this repository -- see `docs/REVIEW_REQUIRED.md`.

Before treating this as reproducible end-to-end, resolve the open items in `docs/REVIEW_REQUIRED.md`.

## Contact

euan@stanford.edu; bgomes@stanford.edu
