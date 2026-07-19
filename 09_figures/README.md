# 09_figures

Figure generation. Pulls together outputs from the burden test, heritability, MR, PWAS, colocalization, SMR-HEIDI, and survival analyses into the final figures and supplementary tables. Run last, after `04_pwas/`, `06_mr/`, and `08_clinical_associations/` have produced their outputs.

## File

### `01_Fibrosis_Figures.ipynb`

One notebook organized into sections by markdown header, each reading a specific upstream result file and producing one or more figures/tables:

| Section | Reads | Produces |
|---|---|---|
| Burden Test Results | `./data/burden_test_1025/significant_variants.txt`, `./data/burden_test_latent_1025/latent_significant_variants.txt` | Volcano plots, a gene-overlap Venn diagram, `rare_variant_analysis.png` + 3 supplementary-table CSVs |
| Heritability Results | LDSC h² values | A forest plot of heritability estimates with 95% CI |
| MR | `MR_T1_preprint_sig.txt` / `MR_latent_preprint_sig.txt` | Forest plots (`MR_latent_grant_sig.svg`, `MR_t1_grant_sig.svg`), a two-dataset comparison volcano plot (`volcano_comparison_color.svg`), single-dataset volcano plots |
| PWAS | PWAS beta/p-value table | `protein_significance_heatmap.png`/`.pdf` |
| Updated, more comprehensive MR Results | `MR_significant_hits.txt` (old) vs. `MR_2_significant_hits.txt` (new) | Overlap/direction-of-effect analysis, a pro-/anti-fibrotic direction-of-effect table per exposure protein |
| Nauffal et al. Manual MR | Published comparison betas/p-values | `septal_t1_mr_forest_plot.svg` |
| COLOC Analysis | `coloc_results_latent_task01_of01.tsv.gz`, `coloc_results_task01_of01.tsv.gz` | Strong-colocalization and separate-causal-variant tables, gene summary |
| SMR-HEIDI Analysis | `./data/MR_experiment/summary_hits.txt` | FDR-corrected causal gene-trait-tissue tables |
| Cox Hazard Models | `./data/survival_analysis_results.csv` (written by `08_clinical_associations/02_mortality_curves_chi_squared.ipynb`) | Figure 1 (top survival associations), Figure 2 (hazard-ratio forest plot), Supplementary Figures 1-2 (full versions) |
