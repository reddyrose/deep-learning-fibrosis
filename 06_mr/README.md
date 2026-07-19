# 06_mr

Two-sample Mendelian randomization of circulating-protein cis-pQTLs against the T1-percentile and CVAE-latent-dimension GWAS results from `05_gwas/`. This folder contains cis-pQTL extraction, LD clumping, the MR execution itself (several historical orchestration variants of the same underlying analysis), and Bonferroni-significance filtering. Colocalization (`colocalization/`) and MR-PRESSO sensitivity analysis (`mr_presso/`) are in their own subfolders with their own READMEs.

## Files, in the order you'd use them

### 1. `clumping_shriya.sh` (+ `clumping_shriya_job.sh` wrapper)
LD-clumps protein GWAS summary files with PLINK (`--clump-kb 100 --clump-p1 5e-5 --clump-p2 1e-3 --clump-r2 0.01`) against a 1000 Genomes hg38 reference panel, to identify independent lead SNPs per protein.
- **Input:** every `*_gwas.txt` file in the current directory.
- **Output:** `r2_001/<prefix>.clumped` per input file.
- **Run:** `sbatch clumping_shriya_job.sh` (which `cd`s into the T1-percentiles GWAS directory and calls `clumping_shriya.sh`), or `bash clumping_shriya.sh` directly from a directory of `*_gwas.txt` files.

### 2. `cis_loop_script.R`
Builds the cis-pQTL exposure files: for each protein's GWAS-with-rsIDs file, filters to the clumped lead SNPs from step 1 that also fall within **±500 kb** of the protein-coding gene's coordinates.
- **Input:** `*_gwas_rsids.txt` files, the matching `.clumped` files from step 1, and an offline Ensembl gene-coordinate lookup table.
- **Output:** `<gene>_cis_subset.tsv` per gene, under `cis_subsets_r2_001/`.
- **Run:** `Rscript cis_loop_script.R` (edit `BASE_DIR` first).

### 3. Run the MR itself -- pick one orchestration variant
All of these implement the same core analysis (harmonize exposure/outcome, run IVW MR via `TwoSampleMR`/`MendelianRandomization`) against every `<cis_subset>.tsv` x `<outcome_gwas>.txt` pair; they differ in how the work is parallelized/chunked, kept here as historical alternatives rather than collapsed into one:

| Script | Strategy | Run |
|---|---|---|
| `MR_shriya_2.R` (called by `MR_job_shriya_2_latent.sh` / `MR_job_shriya_2_percentiles.sh`) | Resumable, `future_lapply`-parallelized, skips pairs already in the output file | `sbatch MR_job_shriya_2_latent.sh` (**set `LATENT_GWAS_DIR` first** -- see `docs/REVIEW_REQUIRED.md`) / `sbatch MR_job_shriya_2_percentiles.sh` |
| `MR_error_handling.R` (templated by `create_scripts.sh` into 20 batch jobs) | Sequential, defensive error handling, periodic checkpoint writes every 500 pairs | `bash create_scripts.sh` to generate the 20 job scripts, then `sbatch` each one |
| `make_pair_list.R` + `run_chunk.R` | Pre-computes the full pair list once, then a SLURM array job processes it in fixed-size (15-pair) chunks | `Rscript make_pair_list.R --protein_roots=<dirs> --brain_path=<dir> --out_file=pair_list.tsv`, then `sbatch --array=1-N` running `run_chunk.R` |
| `make_pair_list.R` + `run_one_pair.R` | Same pair list, one pair per SLURM array task (finer granularity) | as above, then `Rscript run_one_pair.R $SLURM_ARRAY_TASK_ID` per array task |
| `make_pair_list.R` + `run_pairs.R` | Same pair list, single job with 5 parallel workers (no SLURM array) | `Rscript run_pairs.R` |

`run_chunk.R`, `run_one_pair.R`, and `run_pairs.R` all `source("run_mr_core.R")` for the shared `run_mr_pair()` function -- that file isn't run directly.

- **Output (any variant):** a TSV of `exposure_file, outcome_file, ivw_estimate, ivw_se, ivw_pval, n_snps` per pair.

### 4. `find_sig.sh`
Scans the completed MR result TSVs for Bonferroni-significant associations and compiles them into one file.
- **Input:** `INPUT_DIR` = a directory of completed MR result `*.tsv` files.
- **Output:** `significant_associations.txt` (or a custom filename passed as `$1`) -- this is the `mr_table` input expected by `colocalization/COLOC_one.R` and `colocalization/COLOC_latent.R`.
- **Run:** `bash find_sig.sh [output_filename]`.

## Subfolders
- **`colocalization/`** -- `coloc.abf` colocalization of the significant MR hits. See its own README.
- **`mr_presso/`** -- MR-PRESSO pleiotropy/outlier sensitivity analysis of the significant MR hits. See its own README.
