# 06_mr/colocalization

Bayesian colocalization (`coloc.abf`) of the significant MR hits from `06_mr/find_sig.sh`, testing whether the pQTL and GWAS signals at each locus share a single causal variant (as opposed to two distinct, linked signals). One pair of scripts per outcome type -- T1-percentile and CVAE-latent.

## Files

### `COLOC_one.R` (+ `COLOC_T1.sh` wrapper)
Colocalization for **T1-percentile** outcomes, despite the filename "one" not indicating this -- its hardcoded I/O paths (`.../SHMOLLI_hg38_converted_GWASs/T1_percentiles_HHregressed`) and its `COLOC_T1.sh` wrapper make the T1 scope unambiguous.
- **Input:** `significant_associations.txt` (from `06_mr/find_sig.sh`, run against the T1-percentile MR results), the cis-pQTL data (`06_mr/cis_loop_script.R`'s output), the T1-percentile GWAS directory, and a reference allele-frequency file.
- **Filters:** MR screening threshold `p < 5e-5`, minimum 20 shared variants.
- **Output:** `coloc_results_task<NN>_of<NN>.tsv.gz` (exposure, outcome, `pp_h4`, `pp_h3`, n_snps).
- **Run:** `sbatch COLOC_T1.sh` (runs as a SLURM array job -- `SLURM_ARRAY_TASK_ID`/`SLURM_ARRAY_TASK_COUNT` control chunking; defaults to a single task if unset).

### `COLOC_latent.R` (+ `COLOC_latent.sh` wrapper)
The same colocalization logic, for **CVAE-latent-dimension** outcomes.
- **Input:** `significant_associations.txt` (from `06_mr/find_sig.sh`, run against the latent-dimension MR results), same cis-pQTL data, the latent-dimension GWAS directory, and the reference allele-frequency file. Same filters as `COLOC_one.R`.
- **Output:** `coloc_results_latent_task<NN>_of<NN>.tsv.gz`.
- **Run:** `sbatch COLOC_latent.sh`.

Both use the `coloc` R package and report `PP.H4` (shared causal variant) and `PP.H3` (distinct causal variants), matching the manuscript's colocalization methodology. Outputs from both are read together by `09_figures/01_Fibrosis_Figures.ipynb`'s "COLOC Analysis" section.
