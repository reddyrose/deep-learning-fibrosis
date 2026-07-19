# 05_gwas

Phenotype residualization/normalization, PLINK2 GWAS of T1-percentile and CVAE-latent phenotypes, VCF conversion and hg19->hg38 liftover, SNP-ID standardization, and LDSC heritability/genetic correlation.

## Files, in the order you'd use them

### 1. `outliers_residuals_norm.ProblemPhenotypes.R`
Truncates outliers (3-SD winsorization), residualizes T1 phenotypes against covariates (sex, year of birth, genetic PCs 1-5, batch) via linear regression, and quantile-normalizes the residuals -- this is the file GWAS actually reads as `--pheno`.
- **Input:** `cleaned_T1_percentiles_HHregressed.csv_phenotypes_trimmed.txt` + `..._covariates_trimmed.txt` under `./data/shriya/SHMOLLI-output-unet-myocardium-update2/`.
- **Output:** `cleaned_T1_percentiles_HHregressed.no_outliers.residuals.qnorm.txt`.
- **Run:** `Rscript outliers_residuals_norm.ProblemPhenotypes.R` (edit `BASE_DIR` first).
- **Note:** the covariate list in this script is edited to match the phenotype file being produced at the time; other phenotype files (e.g. the PWAS covariate set) use a different covariate list (BMI, height/weight ratio).

### 2. `gwas_final_imputed.sh` / `gwas_VAE.sh`
Run the actual PLINK2 GWAS (`--glm`) of T1-percentile and CVAE-latent-dimension phenotypes respectively against imputed UK Biobank genotypes. Same QC filters in both: `--maf 0.01 --mac 20 --geno 0.1 --hwe 1e-15 --mind 0.1`.
- **Input:** UKBB imputed pgen data, a sample-exclusion list, and the residualized/qnorm phenotype file from step 1 (or its VAE-latent analog).
- **Output:** `GWAS_output.*.glm.linear` files (`gwas_final_imputed.sh`) / `gwas_output.*.glm.linear` files (`gwas_VAE.sh`).
- **Run:** `sbatch gwas_final_imputed.sh` / `sbatch gwas_VAE.sh`.

### 3. `convert_gwas_to_vcf.sh` + `annotate_vcf.sh`
Convert one plink2 GWAS summary-stats file into a minimal VCF, then annotate it with dbSNP rsIDs via `bcftools`.
- **Run:** `bash convert_gwas_to_vcf.sh` (produces `mygwas.vcf.gz`), then `bash annotate_vcf.sh` (produces `mygwas_annotated.vcf.gz`). Both have hardcoded paths -- edit `BASE_DIR`/`GWAS_FILE` before running.

### 4. `full_hg38_converter_pipline.sh`
The main, batched hg19->hg38 liftover pipeline: loops over every `*.glm.linear` file in a GWAS output directory (the VAE-latent GWAS output specifically), lifts each to hg38 (`CrossMap`), annotates with dbSNP, and writes both a final VCF and a plain tabular GWAS file per phenotype.
- **Input:** `INPUT_DIR` = a directory of `*.glm.linear` files (e.g. `gwas_VAE.sh`'s output), a chain file, a GRCh38 reference FASTA, a dbSNP VCF.
- **Output:** `<phenotype>_hg38_annotated.vcf.gz(.tbi)` and `<phenotype>_gwas.txt` per phenotype, in `FINAL_OUTPUT_DIR`.
- **Run:** activate a CrossMap conda environment (see inline comment), then `sbatch full_hg38_converter_pipline.sh`.

### 5. `snp-standardization-workflow.sh` (current) / `snp-standardization-workflow_v1.sh` (earlier version, kept for reference)
Standardizes SNP IDs (a mix of `CHR:POS:REF:ALT` and rsIDs) to consistent rsIDs via Ensembl VEP, run in a Singularity container. `_v1.sh` is an earlier version missing the `--dir_cache`/`--species`/`--assembly`/`--fork 8` flags and the VEP-failure guard that the current version has.
- **Input:** every `.txt`/`.tsv`/`.gz` file in `INPUT_DIR` (a header row + SNP ID in column 3 expected).
- **Output:** `<name>_standardized.txt` per input file.
- **Run:** `sbatch snp-standardization-workflow.sh` (requires `singularity` and a local VEP cache).

### 6. `ldsc_h2_SR.py` + `summary.sh`
Batch-runs LDSC munging, heritability (h2), and all-pairwise genetic-correlation (rg, including cross-category T1-vs-latent) across every GWAS result file, then `summary.sh` parses the resulting `.log` files into one heritability summary table.
- **Input:** `GWAS_results/` and `VAE_GWAS/` directories of `*.glm.linear` files; an LDSC install (`munge_sumstats.py`, `ldsc.py`) and LD reference panel (`eur_w_ld_chr` + `w_hm3.snplist`).
- **Output:** munged sumstats + h2/rg logs under `./data/shriya/ldsc/{munge_statistics,h2,rg}/...`; `summary.sh` then writes `summary.txt` (Phenotype, h2, SE, p_value) from the h2 logs.
- **Run:** `python ldsc_h2_SR.py` (edit `BASE_DIR`/`LDSC_DIR`/`LD_REF_DIR` first), then `cd` into an `h2/<category>/` log directory and run `bash summary.sh`.

### `transfer_gwas.sh`
A one-off file-organization utility that copies base GWAS output files from a sensitivity-analysis working directory into a clean archival directory. Not part of the main pipeline sequence.
