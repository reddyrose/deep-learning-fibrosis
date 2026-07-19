# 06_mr/mr_presso

MR-PRESSO (outlier detection, global pleiotropy test, distortion test) as a sensitivity analysis for pleiotropy on the significant MR hits, run one protein-outcome pair at a time via a SLURM array job, then combined into summary tables.

## Files, in the order you'd use them

### 1. `mrpresso_pairs.txt` / `mrpresso_pairs_2.txt`
Manifests of protein-outcome pairs to run MR-PRESSO on (whitespace-separated, 2 columns, no header: `<gene_symbol> <outcome_name>`). `mrpresso_pairs_2.txt` (20 rows) is the file `run_MR_PRESSO.sh` reads; `mrpresso_pairs.txt` (37 rows) is kept as an alternate manifest.

### 2. `run_MR_PRESSO.R` (+ `run_MR_PRESSO.sh` SLURM array wrapper)
Runs MR-PRESSO for a single protein-outcome pair: a raw MR estimate plus outlier detection, a global pleiotropy test, and a distortion test (5,000 permutations).
- **Input (positional CLI args):** `protein_name outcome_name protein_dir outcome_dir`. Reads CAUSE-format files (`snp, beta_hat, seb, A1` columns) for both exposure and outcome; requires at least 3 harmonized SNPs.
- **Output:** under `<outcome_dir>/${RESULTS_SUBDIR}/` (`RESULTS_SUBDIR` from the `$MRPRESSO_RESULTS_SUBDIR` environment variable — must be set): `<pair>_main_results.csv`, `_global_test.csv`, `_outlier_test.csv`, `_distortion_test.csv`, `_outlier_snps.csv` (if any), plus `.rds` intermediates.
- **Run (via the wrapper):** `sbatch run_MR_PRESSO.sh`, which loops `--array=1-20` over `mrpresso_pairs_2.txt` and calls `Rscript run_MR_PRESSO.R <protein_name> <outcome_name> <protein_dir> <outcome_dir>` per array task.

### 3. `combine_MR_PRESSO.R`
Aggregates every pair's per-pair CSVs from step 2 into combined summary tables with significance/pleiotropy/outlier-correction QC flags.
- **Input:** all `*_main_results.csv`, `*_global_test.csv`, `*_distortion_test.csv` files under `<output_dir>/${RESULTS_SUBDIR}/` (same `$MRPRESSO_RESULTS_SUBDIR` env var as step 2 -- must match).
- **Output:** `mrpresso_all_results_summary.csv`, `mrpresso_all_main_results.csv`, `mrpresso_all_global_tests.csv`.
- **Run:** `MRPRESSO_RESULTS_SUBDIR=<subdir> Rscript combine_MR_PRESSO.R`.
