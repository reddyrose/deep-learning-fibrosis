# Deep learning-derived spatial phenotypes and proteome-wide causal inference identify therapeutic targets for cardiac fibrosis

## Overview

Myocardial fibrosis is nearly ubiquitous across major forms of heart disease and is an independent predictor of heart failure, arrhythmia, and sudden cardiac death. No therapy reliably reverses established fibrosis, and diffuse fibrosis is difficult to characterise beyond coarse, scalar summaries of cardiac MRI T1 mapping. Native T1 mapping non-invasively quantifies diffuse myocardial fibrosis, with elevated T1 reflecting collagen deposition and altered tissue composition, but clinical practice typically reports T1 as a single mean value per subject, discarding most of the spatial and distributional information the map contains.

This project uses deep learning to recover that full spatial and distributional structure. In 50,239 UK Biobank participants, nine distributional and 16 spatial T1 phenotypes are extracted from native T1 maps and combined with genome-wide and proteome-wide association studies across circulating proteins, followed by cis-protein quantitative-trait loci (cis-pQTL) Mendelian randomisation, to identify causal mediators of fibrosis and prioritise candidate therapeutic targets.

The pipeline has two halves:

**Phenotyping (imaging to genetics).** Raw DICOM T1 maps from UK Biobank are converted to images, a U-Net is trained to segment the myocardium, and a convolutional variational autoencoder (CVAE) is trained on the segmented myocardium to encode spatial remodelling patterns in a 16-dimension latent space. The CVAE latent dimensions and a set of T1 percentile/distribution metrics are treated as GWAS phenotypes. Heritability (LDSC) and genetic association testing show that these phenotypes are heritable and capture loci that mean T1 alone would miss.

**Causal inference (genetics to protein to target).** The same phenotypes are the outcome in a proteome-wide association study (PWAS) against circulating Olink proteomics, and the outcome in two-sample Mendelian randomisation using cis-pQTLs as instruments for thousands of circulating proteins, with colocalization (`coloc.abf`) and MR-PRESSO used to guard against confounding by linkage and pleiotropy. Proteins that survive both screens are prioritised as causal candidates, cross-checked against STRING-db protein-protein interaction networks, and replicated in an independent cohort using deCODE Genetics proteomics summary statistics. Clinical relevance is established separately with Kaplan-Meier/Cox survival analysis and chi-squared disease-prevalence testing against the same phenotypes.

![Study overview: U-Net myocardial segmentation, CVAE encoding of T1 spatial distribution, and downstream genomic, proteomic, epidemiological, and causal inference analyses](study_overview.png)

## Repository structure

Each folder is numbered in pipeline order and has its own `README.md` describing every file in it: what it is, what it reads and writes, and the command to run it.

| Folder | Stage |
|---|---|
| [`01_imaging/`](01_imaging/README.md) | DICOM to PNG preprocessing, U-Net myocardium segmentation (training and deployment), mask quality control, SAM fine-tuning. |
| [`02_vae/`](02_vae/README.md) | CVAE training and deployment, latent-dimension extraction, reconstruction-quality evaluation, attention mapping. |
| [`03_phenotypes/`](03_phenotypes/README.md) | Phenotype QC, hematocrit regression, disease-status annotation, sample/ID mapping, and covariate-table preparation. |
| [`04_pwas/`](04_pwas/README.md) | Phenotype/covariate preparation, the per-protein OLS regression that produces the PWAS result tables, and delta-rank disease-association testing. |
| [`05_gwas/`](05_gwas/README.md) | Phenotype residualization/quantile-normalization, PLINK2 GWAS, VCF conversion, liftover, SNP-ID standardization, LDSC heritability/genetic correlation. |
| [`06_mr/`](06_mr/README.md) | cis-pQTL extraction, LD clumping, two-sample Mendelian randomisation, colocalization (`06_mr/colocalization/`), and MR-PRESSO sensitivity analysis (`06_mr/mr_presso/`). |
| [`07_decode_validation/`](07_decode_validation/README.md) | Format conversion for external MR replication in the deCODE Genetics cohort. |
| [`08_clinical_associations/`](08_clinical_associations/README.md) | Cross-phenotype correlation, Kaplan-Meier/Cox survival analysis, and chi-squared disease-prevalence testing. |
| [`09_figures/`](09_figures/README.md) | Figure generation, pulling together outputs from the burden test, MR, PWAS, colocalization, and survival analyses. Run last. |

Within each folder, files are numbered by execution order, so directory listing order matches run order. `04_pwas/biomarker_panel_exploratory.ipynb` is left unnumbered: a protein-biomarker machine-learning analysis kept for reference, outside the core reproduction sequence. `03_phenotypes/cardiomyopathy_clustering_exploratory.ipynb` is likewise unnumbered.

Not included in this repository: UK Biobank or other participant-level data; genotype files, proteomic measurements, and summary-statistic result sets; model weights beyond the two CVAE `.weights.h5` files kept for reference (git-ignored); scheduler logs; software environments or licensed reference panels.

## System requirements

### Operating system
Developed and run on Linux (Stanford Sherlock HPC cluster; specific distribution version not recorded). Not tested on macOS or Windows; the code has no OS-specific calls beyond standard file I/O, but this hasn't been verified.

### Software dependencies and versions tested on
Three conda environments were used, and the version numbers below are exactly what was tested -- not general compatibility claims.

- **Primary environment** (`keras_gpu`, Python 3.9.7): everything except the GPU training/deployment steps below. See [`requirements.txt`](requirements.txt) for the full pinned list. Also used: R 4.4, see [`packages.R`](packages.R) (pinned: TwoSampleMR 0.6.14, MendelianRandomization 0.10.0, coloc 5.2.3, MRPRESSO 1.0; unpinned: data.table, dplyr, readr, optparse, future.apply, future, purrr, stringr, renv, ggplot2, matrixStats, preprocessCore, RhpcBLASctl -- `renv` only required if `RENV_DIR` is set).
- **GPU environment** (`VAE`, Python 3.10.15, CUDA 12.4, cuDNN 9.1.1): the U-Net and SAM steps in `01_imaging/` and the CVAE steps in `02_vae/`. See [`requirements-gpu.txt`](requirements-gpu.txt).
- **`crossmap` environment** (Python 3.9.21): hg19-to-hg38 liftover only (`05_gwas/full_hg38_converter_pipline.sh`), via the CrossMap CLI tool (0.7.3).

Packages used in the code without a version recorded in any of the three environments (PyTorch, Hugging Face `transformers`/`datasets`, MONAI, UMAP, Plotly, `ipywidgets`) are listed unpinned in the requirements files -- confirm before submission.

Other command-line tools:
- **PLINK / PLINK2**: GWAS (`05_gwas/gwas_final_imputed.sh`, `05_gwas/gwas_VAE.sh`, PLINK2 2.00a2.3) and LD clumping (`06_mr/clumping_shriya.sh`, PLINK 1.90b5.3).
- **LDSC** (`munge_sumstats.py`, `ldsc.py`): heritability and genetic correlation (`05_gwas/ldsc_h2_SR.py`).
- **bcftools**: version 1.16.
- **htslib** (`bgzip`, `tabix`): version 1.16, parameterized via `HTSLIB_BIN`.
- **Ensembl VEP**: SNP ID standardization (`05_gwas/snp-standardization-workflow.sh`), run via a Singularity container.

### Non-standard hardware
An NVIDIA GPU (CUDA 12.4-compatible) is required for `01_imaging/`'s U-Net training/deployment and SAM fine-tuning, and for `02_vae/`'s CVAE training/evaluation/deployment. As run on Sherlock (per each script's SLURM header): CVAE training requested 1 GPU and 100GB RAM (`02_vae/train_VAE.sh`, ~20hr wall time); SAM fine-tuning requested 1 GPU and 100GB RAM (`01_imaging/deploy_fine_tune_sam_myocardium_autobounding_box.sh`, ~48hr); CVAE deployment requested 1 GPU and 6GB RAM (~9hr). No specific GPU model is recorded. The non-GPU pipeline stages (GWAS, Mendelian randomisation, colocalization) requested up to 64GB RAM and multi-day wall time on CPU-only nodes -- see each folder's `.sh` scripts for exact `#SBATCH` resource requests.

## Installation guide

### Instructions
1. Clone this repository.
2. Create the primary conda environment and install Python dependencies: `conda create -n fibrosis python=3.9.7 && conda activate fibrosis && pip install -r requirements.txt`.
3. If running the GPU steps (`01_imaging/` U-Net/SAM, `02_vae/` CVAE), create a second environment: `conda create -n fibrosis-gpu python=3.10.15 && conda activate fibrosis-gpu && pip install -r requirements-gpu.txt`. Requires a CUDA 12.4-compatible NVIDIA GPU and driver, installed separately.
4. Install R 4.4 and run `Rscript packages.R` to install the R dependencies.
5. Install the command-line tools listed above (PLINK/PLINK2, LDSC, bcftools, htslib, Ensembl VEP) separately; none are installed by the steps above.

### Typical install time
Measured directly: `pip install -r requirements.txt` took 32 seconds, and `pip install -r requirements-gpu.txt` took 53 seconds, each into a clean virtual environment on a standard broadband connection. Two caveats on these numbers: they used the latest compatible package versions rather than the exact pins above (Python 3.9.7/3.10.15 were unavailable to test directly), and the GPU install was measured on a CPU-only TensorFlow/PyTorch build -- the Linux CUDA-bundled wheels used on Sherlock pull in several additional multi-hundred-MB `nvidia-*` CUDA library packages and will take meaningfully longer, plausibly several minutes depending on connection speed. Neither number includes NVIDIA driver/CUDA toolkit installation, which is system-dependent. R package installation via `packages.R` was not benchmarked; compiling `coloc`/`MRPRESSO` from source if binaries aren't available can take 10-20 minutes.

## Data availability

This project uses UK Biobank data, available to approved researchers under application 22282; UK Biobank data cannot be redistributed and are not included in this repository. deCODE Genetics proteomics summary statistics used for external replication (`07_decode_validation/`) are available via Eldjarn et al., *Nature* 2023, at https://www.decode.com/summarydata/ (GWAS summary statistics for all 2,931 Olink assays and all 4,907 SomaScan assays).

## Configuring data paths

Each script uses a `BASE_DIR` variable (and, where relevant, `LIB_DIR`/`RENV_DIR`/`UKBB_DIR`/`HTSLIB_BIN`) at the top of the file, or relative paths of the form `./data/...` in the notebooks. Set `BASE_DIR` to the root of your data directory, or place/symlink your data under a `data/` directory at the repository root matching each subfolder's relative references.

## How to reproduce

Run the numbered folders in order, 1 through 9. Each folder's README gives the exact file-by-file sequence and command; the summary below is the pipeline at a glance:

1. **`01_imaging/`**: DICOM to PNG to trained U-Net to deployed segmentation masks and T1 percentile statistics, quality-controlled.
2. **`02_vae/`**: CVAE trained on the segmented myocardium, evaluated, deployed to extract latent dimensions at scale.
3. **`03_phenotypes/`**: Mask QC and hematocrit regression, ID/ancestry mapping, disease-status annotation, per-group covariate preparation, and a myocardium-vs-septum validation check.
4. **`04_pwas/`**: Phenotype/covariate preparation, per-protein OLS regression (PWAS), delta-rank disease-association testing.
5. **`05_gwas/`**: Phenotype residualization/normalization, PLINK2 GWAS, VCF/liftover/SNP-ID pipeline, LDSC.
6. **`06_mr/`**: cis-pQTL extraction, LD clumping, two-sample MR, colocalization, MR-PRESSO.
7. **`07_decode_validation/`**: deCODE summary-statistic conversion for external MR replication.
8. **`08_clinical_associations/`**: Cross-phenotype correlation, survival analysis, disease-prevalence testing.
9. **`09_figures/`**: Figures, run last once everything above has produced its outputs.

STRING-db protein-protein interaction analysis, final protein prioritisation, and the deCODE MR-replication comparison were performed using `06_mr/`'s existing scripts against the deCODE-converted inputs, rather than by separate dedicated code.

## Contact

euan@stanford.edu; bgomes@stanford.edu
