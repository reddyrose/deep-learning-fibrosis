# ---- 3) Define a function to run MR for each pair -------------------
run_mr_pair <- function(exp_file, out_file, pair_idx) {
  cat("\n============================================\n")
  cat("Pair index:", pair_idx, "\n")
  cat("Exposure file:", exp_file, "\n")
  cat("Outcome file: ", out_file, "\n")
  
  # 3a) Read exposure data
  pqtl_df <- read_tsv(exp_file, show_col_types = FALSE)
  cat("Exposure raw rows:", nrow(pqtl_df), "\n")
  if (nrow(pqtl_df) == 0) {
    cat("No exposure SNPs. Skipping.\n")
    return(NULL)
  }
  
  # 3b) Read outcome data
  brain_df <- read_tsv(out_file, show_col_types = FALSE)
  cat("Outcome raw rows:", nrow(brain_df), "\n")
  if (nrow(brain_df) == 0) {
    cat("No outcome SNPs. Skipping.\n")
    return(NULL)
  }
  
  # 3c) Format data for TwoSampleMR
  exp_dat <- format_data(
    pqtl_df,
    type               = "exposure",
    snp_col            = "ID",
    beta_col           = "BETA",
    se_col             = "SE",
    effect_allele_col  = "ALT",
    other_allele_col   = "REF",
    pval_col           = "P"
  )
  exp_dat$id.exposure <- "exposure"
  
  out_dat <- format_data(
    brain_df,
    type               = "outcome",
    snp_col            = "ID",
    beta_col           = "BETA",
    se_col             = "SE",
    effect_allele_col  = "ALT",
    other_allele_col   = "REF",
    pval_col           = "P"
  )
  out_dat$id.outcome <- "outcome"
  cat("After format_data(outcome), rows:", nrow(out_dat), "\n")
  
  # 3d) Harmonize exposure & outcome
  dat_harm <- harmonise_data(exposure_dat = exp_dat, outcome_dat = out_dat)
  cat("After harmonise_data, rows:", nrow(dat_harm), "\n")
  if (nrow(dat_harm) == 0) {
    cat("No overlapping SNPs after harmonization. Skipping.\n")
    return(NULL)
  }
  
  cat("Harmonised data columns:\n")
  print(colnames(dat_harm))
  
  # 3e) Rename columns for MendelianRandomization input
  merged_df <- dat_harm %>%
    dplyr::rename(
      betaX = `beta.exposure`,
      seX   = `se.exposure`,
      pX    = `pval.exposure`,
      betaY = `beta.outcome`,
      seY   = `se.outcome`,
      pY    = `pval.outcome`
    ) %>%
    dplyr::select(SNP, betaX, seX, pX, betaY, seY, pY)
  
  cat("merged_df rows:", nrow(merged_df), "\n")
  
  # 3f) Create MR input object
  mr_input_obj <- mr_input(
    bx   = merged_df$betaX,
    bxse = merged_df$seX,
    by   = merged_df$betaY,
    byse = merged_df$seY
  )
  
  # 3g) Run IVW
  # If your version of MendelianRandomization doesn't support model="fixed",
  # remove that argument. By default, it does a fixed-effect IVW anyway.
  ivw_res <- MendelianRandomization::mr_ivw(mr_input_obj, model = "fixed")
  
  # 3h) Build the results row
  out_result <- data.frame(
    exposure_file = basename(exp_file),
    outcome_file  = basename(out_file),
    ivw_estimate  = ivw_res@Estimate,
    ivw_se        = ivw_res@StdError,
    ivw_pval      = ivw_res@Pvalue,
    n_snps        = nrow(merged_df),
    stringsAsFactors = FALSE
  )
  
  cat("MR result:\n")
  print(out_result)
  
  return(out_result)
}
