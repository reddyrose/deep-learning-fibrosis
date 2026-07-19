# 08_clinical_associations

Cross-phenotype correlation testing (PheWAS-style), and Kaplan-Meier/Cox survival analysis with chi-squared disease-prevalence testing. Both notebooks read the U-Net/CVAE phenotype outputs from `01_imaging/`/`02_vae/` merged with UK Biobank clinical/metabolomic data, and can be run in either order.

## Files

### 1. `01_SHMOLLI_PHEWAS_final.ipynb`
Computes Pearson correlations between T1/CVAE-latent phenotypes and metabolomics and hematocrit-adjusted cardiac phenotypes, plus a Spearman correlation pass over metabolomic measures for the latent dimensions. Saves the significant (Bonferroni-corrected) correlation and p-value tables to CSV under `./data/shriya/SHMOLLI-output-unet-myocardium-update2/`.

### 2. `02_mortality_curves_chi_squared.ipynb`
Requires `03_phenotypes/03_disease_status_annotation.py` to have already been run: its "Disease Grouping" section reads that script's `disease_patient_IDs.txt` output for the HCM, Valvular, Amyloidosis, Ischemic, and Non-Ischemic disease groups.

Three analyses:
- **Kaplan-Meier + Cox proportional hazards survival analysis** — for every T1/CVAE-latent phenotype, tests 5 high/low stratification schemes (median split, 25th/75th/2.5th/97.5th percentile cutoffs) against all-cause mortality, computing log-rank p-values, hazard ratios, and 95% CIs, saved to `survival_analysis_results.csv` (read downstream by `09_figures/`). Also includes cause-specific (CV mortality, STEMI, stroke) Kaplan-Meier curves, and a strain-phenotype (circumferential/longitudinal/radial, AHA-segment) mortality-curve analysis.
- **Nested Cox model comparison** — tests whether CVAE latent dimensions add predictive value for mortality beyond mean T1 alone, across four model configurations (penalization choice, feature grouping, and sample-matching for likelihood-ratio tests).
- **Chi-squared disease-prevalence testing** — for each phenotype, splits patients into quartiles and tests disease prevalence (13 disease groups, ICD-10-derived) across quartiles via chi-squared contingency tables, saving significant associations to `chi2_disease_prevalence.csv`.
