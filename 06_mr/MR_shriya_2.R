#!/usr/bin/env Rscript

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# RENV_DIR should point to an renv project directory, if one is needed; leave
# as "." to skip renv activation and use the default R library search path.
BASE_DIR <- "."
RENV_DIR  <- "."

# Prepend your renv library path so these packages are found first.
if (RENV_DIR != ".") {
  .libPaths(c(file.path(RENV_DIR, "renv/library/linux-centos-7/R-4.4/x86_64-pc-linux-gnu/"), .libPaths()))
}

suppressPackageStartupMessages({
  library(renv)
  if (RENV_DIR != ".") renv::activate(RENV_DIR)

  library(optparse)
  library(MendelianRandomization)
  library(TwoSampleMR)
  library(readr)
  library(dplyr)
  library(data.table)
  library(future.apply)
  library(future)
})
Sys.setenv(OMP_NUM_THREADS = 1,
           OPENBLAS_NUM_THREADS = 1,
           MKL_NUM_THREADS = 1,
           VECLIB_MAXIMUM_THREADS = 1)
# ---- 1) Define command-line arguments --------------------------------
option_list <- list(
  make_option(
    c("--protein_roots"),
    type    = "character",
    default = paste(file.path(BASE_DIR, c(
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_01/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_02/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_03/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_04/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_05/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_06/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_07/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_08/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_09/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_10/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_3/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar_2/cis_subsets_r2_001",
      "bruna/vcf_gwas_pa/protein_example/out_tar/cis_subsets_r2_001"
    )), collapse = ","),
    help = "Comma‑separated list of folders that hold *_cis_subset.tsv files.",
    metavar = "character"
  ),
  make_option(
    c("--brain_path"),
    type    = "character",
    default = file.path(BASE_DIR, "bruna/vcf_gwas_pa/MR_experiment/brain_gwas"),
    help    = "Path to folder containing brain GWAS txt files.",
    metavar = "character"
  ),
  make_option(
    c("--out_file"),
    type    = "character",
    default = file.path(BASE_DIR, "bruna/vcf_gwas_pa/MR_experiment/cis_scripts/brain_pQTL_MR.tsv"),
    help    = "Output TSV filename.",
    metavar = "character"
  )
)

parser <- OptionParser(option_list = option_list)
opt    <- parse_args(parser)

cat("Brain path:  ", opt$brain_path,   "\n")
cat("Output file: ", opt$out_file,     "\n\n")

# ---- 2) Gather pQTL and brain GWAS files ----------------------------
protein_roots <- strsplit(opt$protein_roots, ",")[[1]] |> trimws()

pqtl_files <- unlist(lapply(
  protein_roots,
  list.files,
  pattern    = "_cis_subset\\.tsv$",
  full.names = TRUE
))
brain_files <- list.files(
  path       = opt$brain_path,
  pattern    = "_gwas\\.txt$",
  full.names = TRUE
)

if (length(pqtl_files) == 0) {
  stop("No *_cis_subset.tsv files found in any protein_roots folder!")
}
if (length(brain_files) == 0) {
  stop("No matching _gwas.txt files found in brain_path!")
}

# ── A.  Load an existing results table if it is already on disk ─────────
results_done <- NULL
if (file.exists(opt$out_file)) {
  results_done <- read_tsv(opt$out_file, show_col_types = FALSE)
  cat("🔄  Found existing results with", nrow(results_done), "rows\n")
}

# ── B.  Build list of pairs and drop those already finished ─────────────
pairs_df <- expand.grid(
  exposure_file = pqtl_files,
  outcome_file  = brain_files,
  stringsAsFactors = FALSE
)

if (!is.null(results_done)) {
  pairs_df <- dplyr::anti_join(
    pairs_df,
    results_done %>% 
      select(exposure_file, outcome_file) %>% 
      distinct(),
    by = c("exposure_file", "outcome_file")
  )
}
cat("📋  Pairs still to run:", nrow(pairs_df), "\n")

if (nrow(pairs_df) == 0) {
  cat("✅  Nothing new to do — exiting\n")
  quit(save = "no")
}

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
    snp_col            = "SNP",
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

# ---- 4) Parallelize across all pairs with future_lapply ------------

n_cores <- as.integer(Sys.getenv("SLURM_CPUS_PER_TASK", "1"))
plan(multisession, workers = n_cores)

results_list <- future_lapply(
  X = seq_len(nrow(pairs_df)),
  FUN = function(i) {
    run_mr_pair(
      exp_file = pairs_df$exposure_file[i],
      out_file = pairs_df$outcome_file[i],
      pair_idx = i
    )
  },
  future.seed = TRUE
)

# ---- 5) Filter out NULL results and combine --------------------------
results_list <- Filter(Negate(is.null), results_list)

results_df <- if (length(results_list)) {
  data.table::rbindlist(results_list, use.names = TRUE)
} else {
  data.frame()
}

cat("\nAll done! We have", nrow(results_df), "rows of results.\n")

# ── C.  Append new rows to the results file ─────────────────────────────
if (nrow(results_df)) {
  write.table(
    results_df,
    file      = opt$out_file,
    sep       = "\t",
    row.names = FALSE,
    quote     = FALSE,
    col.names = !file.exists(opt$out_file),  # header only if file absent
    append    = TRUE
  )
  cat("✅  Added", nrow(results_df), "rows to", opt$out_file, "\n")
} else {
  cat("⚠️  No new MR pairs succeeded this round\n")
}


cat("Wrote results to:", opt$out_file, "\n")

