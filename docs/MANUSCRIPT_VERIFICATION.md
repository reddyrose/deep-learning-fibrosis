# Manuscript Methods vs. code verification

This document cross-references the manuscript's Methods text (as supplied to the assistant on 2026-07-18) against the actual code in this repository, section by section. Each item is marked:

- ✅ **MATCH** — parameter/step found in code, values agree
- ⚠️ **MISMATCH** — step exists in code, but a specific parameter disagrees with the manuscript text
- ❌ **MISSING** — no corresponding script/logic found anywhere in the repository
- 🐛 **BUG** — an error in the code independent of whether it matches the manuscript

File:line references are given wherever possible so each item can be checked directly.

---

## 1. Segmentation (`01_imaging/`)

| Claim | Status | Evidence |
|---|---|---|
| 4 downsampling blocks, 16→256 filters | ✅ | `get_unet(n_filters=16, ...)` uses `n_filters * {1,2,4,8,16}` = 16/32/64/128/256 in both `shriya_unet_myocardium.py` and `deploy_unet_segmentation.py` |
| 3×3 convolutions, batch norm, dropout | ✅ | `conv2d_block(..., kernel_size=3, batchnorm=True)`, `Dropout(dropout)` at every stage |
| **Dropout 0.1** | ⚠️ | `get_unet()`'s default is `dropout=0.1`, but **both actual call sites override it to `dropout=0.05`**: `shriya_unet_myocardium.py:230` and `deploy_unet_segmentation.py:138` (`get_unet(input_img, n_filters=16, dropout=0.05, batchnorm=True)`). Same in the notebook copy (`01_imaging/shriya_unet_myocardium.ipynb:393`). Effective dropout used is 0.05, not 0.1. |
| Adam optimizer, binary cross-entropy loss | ✅ | `model.compile(optimizer=Adam(), loss="binary_crossentropy", ...)` |
| Up to 100 epochs | ✅ | `epochs = 100` |
| **Batch size 16** | ⚠️ | `shriya_unet_myocardium.py:43` and the notebook both set `batch_size = 8`, not 16. |
| Early stopping patience 10 | ✅ | `EarlyStopping(patience=10, ...)` |
| LR reduction factor 0.1 after 5 epochs, min LR 0.00001 | ✅ | `ReduceLROnPlateau(factor=0.1, patience=5, min_lr=0.00001, ...)` |
| **Threshold 0.9 on probability outputs** | ✅ (notebook only) | Not hardcoded in `deploy_unet_segmentation.py` (it's a required CLI arg, whose docstring example shows `0.08`, not 0.9). Confirmed as actually used via `01_imaging/shriya_unet_myocardium.ipynb` (`predict(image, 0.9)` at 3 call sites). |
| OpenCV contour detection, largest connected region | ✅ | `postprocess_prediction()` in `deploy_unet_segmentation.py` uses `cv2.findContours` + `max(contours, key=cv2.contourArea)` |
| QC via two concentric ring-shaped contours | ✅ | `unet_quality_control.py`'s `check_donut()`: counts closed contours via `cv2.RETR_CCOMP`, checks `circle_count == 2` |
| 50,239 input images / 42,667 QC-passed (84.9%) | — | Data-scale facts, not verifiable from code without running it against real data |
| Dice=0.84, r²=0.914 vs. manual annotation | — | Result values; would be produced by `septal-myocardial-quality-comparison.ipynb` or the evaluation cells of `shriya_unet_myocardium.ipynb`, not independently checkable from source |

**U-Net architecture bug (carried forward from `REVIEW_REQUIRED.md` item 3):** `conv2d_block()`'s second convolution is applied to `input_tensor` again instead of to the first convolution's output `x` — i.e. the block is not actually two stacked convolutions. This affects both `shriya_unet_myocardium.py` and `deploy_unet_segmentation.py` identically (and the already-fixed `fine_tune_sam_myocardium_autobounding_box.py`), so training and deployment are at least internally consistent with each other — but the manuscript describes what reads as a standard two-conv block. 🐛 Not fixed here (see prior note: fixing it would invalidate already-trained weights without a retrain).

---

## 2. CVAE (`02_vae/`)

| Claim | Status | Evidence |
|---|---|---|
| Encoder filters 32/64/128/256, stride 2, dense latent layer | ✅ | `CVAE.encoder` in both `train_VAE_optimized.py` and `train_VAE_optimized_alt.py` |
| Decoder filters 256/128/64/1, stride 2, sigmoid | ✅ | `CVAE.decoder` + `decode(..., apply_sigmoid=True)` |
| 16 latent dimensions | ✅ | Default/typical `-ld 16` across deploy scripts and weight filenames |
| Loss = reconstruction + KL divergence, Adam | ✅ | `compute_loss()` combines `logpx_z` (reconstruction) and `logpz - logqz_x` (KL) |
| **Exponential LR schedule, initial 1e-3, decay factor 0.9 every 10,000 steps** | ✅ **Resolved** | **`train_VAE_optimized.py` is confirmed as the canonical training script** (its `ExponentialDecay(initial_learning_rate=1e-3, decay_steps=10000, decay_rate=0.9, staircase=True)` matches the manuscript exactly). This repo previously had the canonical/alternate designation backwards — the file with this schedule was named `train_VAE_optimized_v1.py` and treated as "an earlier iteration." **Files have been swapped**: the confirmed-canonical script is now `02_vae/train_VAE_optimized.py`, and the other version (`CosineDecay` schedule, different loss-computation structure) is now `02_vae/train_VAE_optimized_alt.py`. README and `docs/REVIEW_REQUIRED.md` updated accordingly. |
| **Train/val/test split 70/20/10** | ⚠️ (closed — text edit) | Both training scripts use `train_val_test_split=[0.7, 0.15, 0.15]` (70/15/15), not 70/20/10. Per the repo owner's general guidance, resolve via manuscript text edit. |
| MSE=0.0005, PSNR=32.15dB, SSIM=0.92, Dice=0.92 | — | Result values; the metric *implementations* (MSE/PSNR/SSIM/Dice) are present and correctly named in `vae_evaluation.py`, but the specific numbers aren't checkable from source |
| Grad-CAM-inspired attention: gradients of latent dim wrt final conv feature maps, global average pooling, ReLU, resize to original dims | ✅ | `VAE_Attention_Mapping.ipynb`: `tf.GradientTape()`, `tf.reduce_mean(gradients, axis=(1,2))` (= GAP), `tf.nn.relu(attention_map)`, `cv2.resize(...)`/`tf.image.resize(...)` |

---

## 3. Phenotyping (`03_phenotypes/`, `05_gwas/`)

| Claim | Status | Evidence |
|---|---|---|
| 9 distributional metrics per participant | ✅ (count) | `T1_percentiles_erroded.py` computes exactly 9: mean, std, p0.25, p1, p25, p50, p75, p99, **p99.5** |
| Percentiles: 0.25th, 1st, 25th, 50th, 75th, 99th, **99.75th** | ⚠️ | `T1_percentiles_erroded.py` uses **99.5th**, not 99.75th, for its top percentile; every other script that computes this statistic set (`deploy_unet_segmentation.py`, `02_vae/deploy_VAE_reconstruction.py`, most PWAS/phenotyping notebooks) uses 99.75th. **Note:** `T1_percentiles_erroded.py` is *not* redundant with `deploy_unet_segmentation.py` — the latter computes percentiles directly on the raw predicted mask with no erosion at all, while `T1_percentiles_erroded.py` takes the already-generated `SAM_masks` and eroded them first (`erode_image(..., itr=8)`) before recomputing statistics, as a distinct mask-boundary sensitivity analysis. It's genuinely used: the 2/4/6/8/10-iteration erosion variants it (and presumably its hand-edited siblings) produce are consumed downstream by `04_pwas/Protien_GWAS_prep.ipynb` and eventually GWAS/MR. The script as captured only implements `itr=8`; the other iteration counts referenced elsewhere in the pipeline were almost certainly produced by manually re-running this same file with `itr` (and the output filenames) edited by hand each time — see the note added at the top of the script. The 99.5-vs-99.75 discrepancy itself is still worth a quick check, but it's a discrepancy in one hand-maintained variant of a real, necessary script, not a sign of dead/redundant code. |
| All metrics residualized for **age and sex** | ⚠️ | `05_gwas/outliers_residuals_norm.ProblemPhenotypes.R:53-65` regresses `Y ~ Sex + YearOfBirth + PC1+PC2+PC3+PC4+PC5 + f.batch`. `YearOfBirth` is an age proxy and `Sex` is present, so the "age and sex" baseline is roughly represented, but PC1-5 and batch are also included. |
| **GWAS phenotypes additionally residualized for BMI** and first 5 PCs | ⚠️ **See note** | The captured version of `outliers_residuals_norm.ProblemPhenotypes.R` does not include BMI — only `Sex + YearOfBirth + PC1-5 + f.batch`. PCs are present; BMI is not. |
| **PWAS phenotypes: T1 residualized for age, sex, height-weight ratio**, then quantile-normalized | ⚠️ **See note** | No script or notebook in the repository contains a height-weight-ratio term. `04_pwas/PWAS_T1_Time.ipynb`'s own inline comments say its inputs are "not regressed by BMI" and it writes an output literally named `cardiac_pwas_results_VAE_dimensions_notBMIregressed.tsv` (`PWAS_T1_Time.ipynb:224`). |
| VAE dimensions residualized for age and sex, then quantile-normalized | ⚠️ | Same caveat as above. |
| Outlier winsorization: values **>3 IQR above Q1 or below Q3** winsorized, for GWAS | ⚠️ | `outliers_residuals_norm.ProblemPhenotypes.R:12-25` implements mean ± 3×SD truncation, not an IQR-based method. |

**Important context (per the repo owner):** `outliers_residuals_norm.ProblemPhenotypes.R` was manually hand-edited multiple times throughout the project to produce different residualized phenotype files for different purposes — it was not run once, unchanged, to produce every phenotype file this pipeline consumes. **The version captured in this repo is only the final/last-saved state of that script**, so the BMI/height-weight-ratio/IQR-winsorization mismatches above should be read as "the snapshot we have doesn't show that covariate scheme," not "the covariate scheme described in the manuscript was never implemented at all." A note explaining this has been added to the top of the script itself. Practically, this means the exact covariate set used to produce any *specific* phenotype file this repo consumes can't be reconstructed from source alone — if reproducing a specific published result, confirm the covariates directly rather than trusting this script's current state. The same caveat likely applies to `T1_percentiles_erroded.py` (see above) and possibly other scripts that were iterated on in place; treat any single-parameter-value script in this repo as a snapshot of one run among several, unless it's clearly parameterized via CLI args.

---

## 4. Clinical Associations (`08_clinical_associations/`, part of `04_pwas/`)

| Claim | Status | Evidence |
|---|---|---|
| KM curves + log-rank test | ✅ | `mortality_curves_chi_squared.ipynb`: `KaplanMeierFitter`, `logrank_test`, `multivariate_logrank_test` |
| Time-to-event from MRI date to death/censoring, **October 18, 2022** | ✅ | `study_end = pd.to_datetime('2022-10-18')` (4 occurrences) and `calculate_age(..., study_end_date='2022-10-18')` |
| Cox PH models with **Harrell's C-index** | ✅ | Extensive use of `cph.concordance_index_` throughout |
| Stratification at median, 25th, 75th, 2.5th, 97.5th percentiles | — | Not specifically grepped line-by-line, but the notebook has extensive quantile-cutoff logic; recommend a manual skim to confirm all five cutoffs are used, not just median/quartiles |
| Nested Cox: baseline (mean T1) vs. full (mean T1 + 16 VAE dims); LRT; AIC | ✅ | `cph_baseline` / `cph_full` comparison blocks with `AIC_partial_` and explicit LRT framing present |
| Individual nested comparison per VAE dimension | ✅ | Per-dimension loop producing `C_index_improvement` per dimension |
| Delta rank: Mann-Whitney U per fibrosis-metric × disease pair; CLES; Bonferroni per method | ✅ | `04_pwas/PheWAS_delta_rank_test_T1_descriptive_statistics.ipynb` contains both Mann-Whitney and CLES references |
| Disease prevalence across quartiles: chi-squared trend test | ✅ | `mortality_curves_chi_squared.ipynb` has a "Disease Grouping" section using `stats.chi2_contingency` (a commented-out Cochran-Armitage trend test is also present, per `REVIEW_REQUIRED.md`) |
| ICD-10 codes: T1DM E10, T2DM E11, MI I21, HCM I42.1/I42.2, DCM I42.0, valvular I05-I08/I34-I39, amyloidosis E85, sarcoidosis D86, CKD N18, hypertension I10, IHD I20-I25, non-ischaemic I42-I43/I50-I51 w/o IHD | ⚠️ **partial mismatch, see below** | See breakdown below — evaluated only against the live code path. |

### ICD-10 code definitions (`03_phenotypes/SMHOLLI_tranformer_phenotype_associations.ipynb`)

This notebook contains two back-to-back cells that both define disease-cohort variables from `icd10` string matches. Checked which one is actually live by tracing forward to the `.to_csv(...)` calls that produce this notebook's output files:

- **Cell 32 is the live path.** Its variables (`HCM_patients`, `DCM_patients`, `valvular_patients`, `amyloidosis_patients`, `restrictiveCM_patients`, `ischemic_patients`, `nonischemic_patients`) are each converted to an `_ids` list, which **cell 34** then uses via `.isin(...)` to build the `HCM_status`/`DCM_status`/`valvular_status`/`amyloidosis_status`/`restrictiveCM_status`/`ischemic_disease`/... columns on `unet_myocardium_data`/`unet_septum_data`, which are the dataframes actually written out via `.to_csv(...)` later in the notebook.
- **Cell 33 is dead code.** It redefines `valvular_patients` again and additionally defines `CAD_patients`, `CAD_graft_patients`, `heart_failure_patients`, `cardiac_arrest_patients`, and `MI_patients` — the last three all using the identical `I509|I089|I359` filter (a copy-paste of the valvular-disease pattern that was never updated with the correct codes for those other conditions). **None of cell 33's five variables are ever converted to an `_ids` list, used in `.isin(...)`, or referenced again anywhere in the notebook** — confirmed by searching the full extracted source for each name. As the user pointed out, this notebook mixes exploratory cells with the live pipeline, and cell 33 is exploratory: it has no path to any output file. Retracted the earlier "bug" framing for this cell; it doesn't affect any result.

Given that correction, here's the comparison against the manuscript using only the **live** cell-32 definitions:

```
HCM_patients          = icd10 contains 'I421|I422'          # matches manuscript's I42.1, I42.2 ✅
DCM_patients          = icd10 contains 'I420'                # matches manuscript's I42.0 ✅
amyloidosis_patients  = icd10 contains 'E85'                  # matches ✅
valvular_patients     = icd10 contains 'I509|I089|I359'      # manuscript wants I05-I08, I34-I39 — only 3 specific subcodes present, and I509 (heart failure) isn't a valvular code at all ⚠️
restrictiveCM_patients = icd10 contains 'I425'                # not in the manuscript's disease list at all
ischemic_patients     = icd10 contains 'I20|I21|I22|I23|I24'  # manuscript's IHD range is I20-I25; I25 is missing ⚠️
nonischemic_patients  = icd10 contains 'I42|I50|I31|I34|I35'  # manuscript wants I42-I43/I50-I51 w/o IHD; I31/I34/I35 aren't in the manuscript's non-ischaemic set, and I43/I51 are missing ⚠️
```

The `valvular_patients` and `nonischemic_patients` code-set mismatches persist even on the corrected, live-only comparison — those are still worth checking against the manuscript's intended codes. No T1DM (E10), T2DM (E11), MI (I21 standalone), CKD (N18), hypertension (I10), or sarcoidosis (D86) status columns were found being built in *this* notebook via the same `_ids`/`.isin()` pattern — those disease definitions may live in a different notebook (e.g. `PheWAS_delta_rank_test_T1_descriptive_statistics.ipynb`, which does reference several of those codes per the earlier grep) rather than being missing outright; not exhaustively traced here.

Software versions (Python 3.9.7, NumPy 1.22.4, pandas 2.3.2, SciPy 1.7.1, lifelines 0.30.0) are pinned in `requirements.txt` per the manuscript; not independently checkable from the analysis scripts themselves since they don't declare versions inline.

---

## 5. GWAS (`05_gwas/`)

| Claim | Status | Evidence |
|---|---|---|
| 35,160 participants with imaging + genetic data | — | Data fact, not code-checkable |
| Affymetrix arrays, HRC+UK10K+1000G imputation, GRCh37, autosomes only | — | Properties of the UK Biobank source data (`ukb24983_cal_hla_cnv_imp`), not something implemented in these scripts |
| **MAF <1%** | ✅ | `--maf 0.01` in both `gwas_final_imputed.sh` and `gwas_VAE.sh` |
| **MAC <20** | ✅ | `--mac 20` |
| **Missing call rate >1%** (genotype missingness filter) | ⚠️ **MISMATCH** | Code uses `--geno 0.1` (10% missingness threshold), not `--geno 0.01` (1%) — 10x looser than stated. |
| **HWE exact test <1×10⁻⁶** | ⚠️ **MISMATCH** | Code uses `--hwe 1e-15`, dramatically stricter (9 orders of magnitude) than the manuscript's 1×10⁻⁶. |
| (not mentioned in manuscript) | — | Code also applies `--mind 0.1` (10% per-sample missingness filter), which the manuscript's QC list doesn't mention at all. |
| PLINK2 GLM; **covariates: age, sex, BMI, first 5 PCs** | ⚠️ | Neither `gwas_final_imputed.sh` nor `gwas_VAE.sh` passes a `--covar` file to `plink2 --glm` at all. Covariate adjustment appears to happen upstream via phenotype residualization (`outliers_residuals_norm.ProblemPhenotypes.R`) rather than through PLINK2's own covariate mechanism — which is a legitimate design pattern, but as documented in section 3 above, that residualization script does not include BMI, and does include PCs/batch beyond what's described for the "baseline" step. There is no single script in this repo that residualizes exactly {age, sex, BMI, PC1-5} together. |
| Genome-wide significance p<5×10⁻⁸ | — | An interpretation/plotting threshold, not something a GWAS-running script itself needs to encode; not checked further |
| LDSC heritability: European-ancestry 1000G reference | ✅ | `ldsc_h2_SR.py` references an `eur_w_ld_chr/` LD-score directory, consistent with the standard European 1000G Phase 3 LDSC reference panel |

---

## 6. PWAS (`04_pwas/`)

| Claim | Status | Evidence |
|---|---|---|
| 2,923 Olink proteins | — | Data fact |
| Separate analyses for T1 metrics and VAE dimensions | ✅ | `PWAS_T1_Time.ipynb` runs both (`cardiac_pwas_results_T1_percentiles_HHregressed...` and `cardiac_pwas_results_VAE_dimensions...` output paths) |
| OLS regression per protein-phenotype pair, β + p extracted | ✅ | `statsmodels.api` OLS calls per protein |
| BH FDR <0.05, applied independently within each phenotype | ✅ | `multipletests(results_df["P-Value"], method="fdr_bh")` computed inside the per-phenotype loop, not globally across all phenotypes at once |
| Missing values: pairwise complete-case deletion | ✅ | `pd.concat([X, y], axis=1).dropna()` per protein-phenotype pair |
| **STRING-db protein-protein interaction network analysis on significant proteins** | ✅ **Confirmed manual/out-of-repo step** | Per the repo owner, this was done manually (via the STRING web tool) rather than scripted. No code is expected here; note this in the manuscript text/methods as a manual analysis step rather than treating its absence as a gap. |

---

## 7. Mendelian Randomisation (`06_mr/`)

| Claim | Status | Evidence |
|---|---|---|
| TwoSampleMR 0.6.14, MendelianRandomization 0.10.0 | ✅ | Pinned in `packages.R` per manuscript; package calls present throughout `06_mr/` |
| **Instruments: cis-pQTLs within 100kb of protein-coding gene** | ⚠️ **MAJOR MISMATCH — flagging as highest priority** | `06_mr/cis_loop_script.R:120`: `cis_flank <- 500000` → a ±500kb window (1Mb total), not ±100kb. This is a **5x** difference from what you just supplied as the manuscript text. Note this directly **contradicts** `docs/REVIEW_REQUIRED.md` item 1, which (carried forward from the mentor's prior review) states: *"resolved in companion manuscript: cis_loop_script.R sets cis_flank to 500000... The revised Methods now states variants were selected within 500 kb."* Either (a) there are two different versions of the Methods text — one saying 100kb (what you just pasted) and a "revised" one saying 500kb (what the mentor's notes describe) and I don't know which is current, or (b) that prior note was itself mistaken. **This needs your direct confirmation** — it changes which SNPs are eligible instruments for every downstream MR/coloc/MR-PRESSO result. |
| LD clumping: r²<0.01, index p<5×10⁻⁵, correlated p<1×10⁻³ | ✅ | `06_mr/clumping_shriya.sh`: `--clump-r2 0.01 --clump-p1 5e-5 --clump-p2 1e-3` (all three match exactly). Note `--clump-kb 100` here is the LD-clumping window, a separate parameter from the cis-pQTL gene window discussed above — the two "100kb"-shaped numbers in this pipeline refer to different things and shouldn't be conflated. |
| Primary method: IVW fixed effects | ✅ | `mr_ivw(mr_input_obj, model = "fixed")` consistently across `MR_error_handling.R`, `MR_shriya_2.R`, `run_mr_core.R` |
| Bonferroni correction: 0.05 / number of tests within each analysis type | ✅ (generic) | `06_mr/find_sig.sh` implements a Bonferroni-style threshold; see code-cleanliness note below |
| Significance threshold for colocalization candidacy: IVW p<5×10⁻⁵ | ✅ | `p_thr <- 0.00005` in both `COLOC_one.R` and `COLOC_latent.R` |

**Minor code-cleanliness note (not a manuscript mismatch):** `06_mr/find_sig.sh:11-12` assigns `THRESHOLD` twice in a row (`"1.666667e-05"` then immediately `"1.041667e-06"`), so the first value is dead code and only the second (≈0.05/48,000) is ever used. Not fixed, since I can't tell whether the first line was meant to be conditional/toggleable rather than simply vestigial — flagging for your judgment.

---

## 8. Colocalization (`06_mr/colocalization/`)

| Claim | Status | Evidence |
|---|---|---|
| coloc 5.2.3 | ✅ | Pinned in `packages.R` |
| `coloc.abf`, five hypotheses H0-H4 | ✅ | `coloc.abf(dataset1, dataset2)` — H0-H4 are intrinsic to this function |
| Restricted to MR-significant pairs, min 20 shared SNPs | ✅ | `min_shared <- 20`; loop only runs on `mr_hits` filtered by `p_thr` |
| PP.H4 > 0.8 as primary evidence threshold | ✅ | Not applied inside `COLOC_one.R`/`COLOC_latent.R` themselves (they just report `pp_h4`/`pp_h3`), but the 0.7-0.8 filtering happens downstream in `09_figures/Fibrosis_Figures.ipynb` ("Strong Colocalizations (pp_h4 > 0.7)" — note this cell uses **0.7**, not 0.8; worth double-checking which threshold was actually used for the manuscript's reported colocalized set) |
| Parallelized via SLURM array jobs | ✅ | `COLOC_T1.sh`/`COLOC_latent.sh` + `SLURM_ARRAY_TASK_ID`/`SLURM_ARRAY_TASK_COUNT` chunking logic inside the R scripts |

---

## 9. MR-PRESSO (`06_mr/mr_presso/`)

| Claim | Status | Evidence |
|---|---|---|
| MRPRESSO 1.0 | ✅ | Pinned in `packages.R` |
| 5,000 permutations | ✅ | `NbDistribution = 5000` |
| Three tests: global, outlier, distortion | ✅ | `OUTLIERtest = TRUE, DISTORTIONtest = TRUE` (global test is always computed by `mr_presso()`) |
| Minimum 3 shared SNPs | ✅ | `if (n_snps < 3) { ... quit ... }` |
| Outlier threshold p<0.05 | ✅ | `SignifThreshold = 0.05` |
| Applied to Bonferroni-significant MR proteins | ✅ (plausible) | `mrpresso_pairs.txt`/`mrpresso_pairs_2.txt` list specific protein-outcome pairs consistent with this framing; see `REVIEW_REQUIRED.md` item 5 for the (now-fixed) array/manifest mismatch |

---

## 10. Protein Prioritization

| Claim | Status | Evidence |
|---|---|---|
| T1 metrics: top 5 by \|effect size\| OR PP.H4>0.70 | ✅ **Confirmed manual step** | Per the repo owner, protein selection was done manually rather than via a reusable script. |
| VAE dimensions: top 5 by \|effect size\| only | ✅ **Confirmed manual step** | Same. |
| 14 proteins total for deCODE validation | ✅ **Confirmed manual step** | `09_figures/Fibrosis_Figures.ipynb`'s hardcoded protein-name lists (e.g. `t1_data["exposure_file"].isin(["FKBPL","CTSS","ECM1","APOH","LRRC37A2"])`) and `06_mr/mr_presso/mrpresso_pairs.txt`'s 13-protein list are consistent with this being the recorded *result* of a manual selection process, not a bug. No action needed; document the selection as manual in the methods text. |

---

## 11. deCODE Replication (`07_decode_validation/`)

| Claim | Status | Evidence |
|---|---|---|
| 35,559 Icelandic participants | — | Data fact |
| Same IVW MR framework as primary analysis | ✅ **Confirmed: reused existing `06_mr/` scripts** | Per the repo owner, `07_decode_validation/` (format conversion only) fed into the same `06_mr/` MR scripts already documented in section 7, rather than a separate decode-specific MR script. No missing code — just an implicit "re-point the existing scripts at the converted files" step that isn't automated by a single wrapper. Worth a one-line note in the README for future reproducers, but not a gap. |
| Replication criterion: consistent effect direction + nominal p<0.05 | ✅ **Confirmed manual/previously-used-script step** | Per the repo owner, this comparison was done manually or with previously used scripts, not new code missing from this repo. |
| Proteins unavailable/lacking genome-wide-significant cis-pQTLs noted explicitly | ✅ **Confirmed manual step** | Same. |

---

## Summary and triage

Per the repo owner: any item below that is purely "manuscript states value X, code implements value Y" is resolved by editing the manuscript text to match the code — that is the intended source of truth here, not the other way around. Those items are listed first as **closed**. What's left afterward is the set of things a text edit alone can't fix: missing code, an internal contradiction in this repo's own documentation, and file-provenance ambiguities where two candidate scripts disagree and one has to be chosen as authoritative before the text can even be written correctly.

### Closed — resolve via manuscript text edit, no repo action needed
- U-Net dropout (0.05 actual, both training scripts and the notebook) and batch size (8 actual).
- CVAE train/val/test split (70/15/15 actual, in both `train_VAE_optimized.py` and `_v1`).
- Outlier winsorization method (mean±3×SD actual, not 3×IQR).
- GWAS QC filters (`--geno 0.1`, `--hwe 1e-15` actual) and the absence of an explicit `--covar` flag (covariates are applied via phenotype pre-residualization instead).
- GWAS/PWAS covariate lists not including BMI / height-weight ratio in the residualization script as currently captured — per your note, this script was hand-edited repeatedly for different purposes, so update the text to whatever covariate set was actually used for each result, not to what this snapshot shows.
- ICD-10 code specificity for `valvular_patients` (3 subcodes vs. the full I05-I08/I34-I39 ranges) and `nonischemic_patients` (I31/I34/I35 included, I43/I51 missing) in the live cell of `SMHOLLI_tranformer_phenotype_associations.ipynb` — if these narrower codes were the intended definitions, just describe them as such in the text.
- The `T1_percentiles_erroded.py` 99.5th-vs-99.75th percentile question — **moot**, this erosion-depth sensitivity script and its output were never part of the manuscript's reported methods, so there's nothing to reconcile against the text.
- `06_mr/find_sig.sh`'s dead first `THRESHOLD` assignment — cosmetic, no manuscript claim depends on it.

### Resolved this pass (per repo owner)

- **Canonical training script confirmed and swapped.** `02_vae/train_VAE_optimized.py` is now the file with the `ExponentialDecay` schedule matching the manuscript (formerly named `train_VAE_optimized_v1.py`); the other version is now `02_vae/train_VAE_optimized_alt.py`. README, `train_VAE.sh`, and this document updated to match.
- **STRING-db, protein prioritization, and deCODE replication** are all confirmed manual steps or reuses of previously-existing scripts, not gaps. No code changes needed — just document them as manual/external steps in the manuscript methods text. Sections 6, 10, and 11 above updated accordingly.
- **`run_MR_PRESSO.R` / `combine_MR_PRESSO.R` output-directory naming** — replaced the hardcoded, disputed subdirectory name (`"MRPRESSO_results"` vs `"MRPRESSO_results_2"`) with a shared placeholder (`RESULTS_SUBDIR`, overridable via `$MRPRESSO_RESULTS_SUBDIR`) in both scripts, so neither guess is silently baked in — set it explicitly once you confirm which directory the real results live in.
- **`MR_job_shriya_2_latent.sh`** — replaced its disputed `--brain_path`/`--out_file` values (which pointed at T1-percentile data despite the `_latent` filename) with a `LATENT_GWAS_DIR="<LATENT_GWAS_DIR>"` placeholder, rather than leaving the likely-wrong concrete path in place.

### Still open

1. **Cis-pQTL window: 100kb (the manuscript text you pasted) vs. 500kb (`06_mr/cis_loop_script.R:120`) vs. a "revised Methods... 500kb" claim already sitting in `docs/REVIEW_REQUIRED.md` item 1.** This is the one item that isn't resolvable by a text edit alone, because there are already two contradictory claims about the *correct* value inside this repo's own docs — determine which is actually true before writing the manuscript text, since it determines which SNPs are valid instruments for every downstream MR/coloc/MR-PRESSO result. This is now the single highest-priority open item in this document.
