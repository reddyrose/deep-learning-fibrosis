#!/usr/bin/env Rscript

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# LIB_DIR should point to a custom R library location, if one is needed; leave
# as "." to use the default R library search path.
BASE_DIR <- "."
LIB_DIR  <- "."

if (LIB_DIR != ".") .libPaths(c(LIB_DIR, .libPaths()))

suppressPackageStartupMessages({
  #library(renv)
  #renv::activate(file.path(BASE_DIR, "bruna/R_cis_2"))

  library(optparse)
  library(MendelianRandomization)
  library(TwoSampleMR)
  library(readr)
  library(dplyr)
  library(future.apply)
})

# ---- 1) Define command-line arguments --------------------------------
option_list <- list(
  make_option(
    c("--protein_path"),
    type    = "character",
    default = file.path(BASE_DIR, "bruna/vcf_gwas_pa/protein_example/out_tar_4/job_10/cis_subsets_r2_001/"),
    help    = "Path to folder containing protein cis-subset TSVs.",
    metavar = "character"
  ),
  make_option(
    c("--brain_path"),
    type    = "character",
    default = file.path(BASE_DIR, "bruna/vcf_gwas_pa/MR_experiment/brain_gwas"),
    help    = "Path to folder containing GWAS txt files.",
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

cat("Protein path:", opt$protein_path, "\n")
cat("Brain path:  ", opt$brain_path,   "\n")
cat("Output file: ", opt$out_file,     "\n\n")

# ---- 2) Gather pQTL and brain GWAS files ----------------------------
pqtl_files <- list.files(
  path       = opt$protein_path,
  pattern    = "_cis_subset\\.tsv$",
  full.names = TRUE
)

brain_files <- list.files(
  path       = opt$brain_path,
  pattern    = "_gwas\\.txt$",
  full.names = TRUE
)

if (length(pqtl_files) == 0) {
  stop("No matching *cis*subset.tsv files found in protein_path!")
}
if (length(brain_files) == 0) {
  stop("No matching *gwas.txt files found in brain*path!")
}

# Make a data frame of all exposure/outcome pairs
pairs_df <- expand.grid(
  exposure_file = pqtl_files,
  outcome_file  = brain_files,
  stringsAsFactors = FALSE
)

cat("Total pairs to process:", nrow(pairs_df), "\n")

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
  
  # Check if exposure data is valid after formatting
  if (nrow(exp_dat) == 0) {
    cat("No valid exposure SNPs after formatting. Skipping.\n")
    return(NULL)
  }

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
  
  # Check if outcome data is valid after formatting
  if (nrow(out_dat) == 0) {
    cat("No valid outcome SNPs after formatting. Skipping.\n")
    return(NULL)
  }
  
  # Check for any SNPs in common between exposure and outcome
  common_snps <- intersect(exp_dat$SNP, out_dat$SNP)
  if (length(common_snps) == 0) {
    cat("No SNPs in common between exposure and outcome. Skipping.\n")
    return(NULL)
  }
  
  # Filter to only include SNPs that are present in both datasets
  exp_dat <- exp_dat[exp_dat$SNP %in% common_snps, ]
  out_dat <- out_dat[out_dat$SNP %in% common_snps, ]
  
  # Double-check that we have data left after filtering
  if (nrow(exp_dat) == 0 || nrow(out_dat) == 0) {
    cat("No overlapping SNPs after filtering. Skipping.\n")
    return(NULL)
  }

  # 3d) Harmonize exposure & outcome with tryCatch to handle potential errors
  dat_harm <- tryCatch({
    harmonise_data(exposure_dat = exp_dat, outcome_dat = out_dat)
  }, error = function(e) {
    cat("Error in harmonise_data:", e$message, "\n")
    return(NULL)
  })
  
  # Check if harmonization was successful
  if (is.null(dat_harm) || nrow(dat_harm) == 0) {
    cat("No data after harmonization. Skipping.\n")
    return(NULL)
  }
  
  cat("After harmonise_data, rows:", nrow(dat_harm), "\n")

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
  
  # Check if we have enough SNPs for MR (at least 3 is recommended)
  if (nrow(merged_df) < 3) {
    cat("Fewer than 3 SNPs after harmonization. Skipping MR analysis.\n")
    return(NULL)
  }

  # 3f) Create MR input object with error handling
  mr_input_obj <- tryCatch({
    mr_input(
      bx   = merged_df$betaX,
      bxse = merged_df$seX,
      by   = merged_df$betaY,
      byse = merged_df$seY
    )
  }, error = function(e) {
    cat("Error creating mr_input object:", e$message, "\n")
    return(NULL)
  })
  
  if (is.null(mr_input_obj)) {
    cat("Failed to create MR input object. Skipping.\n")
    return(NULL)
  }

  # 3g) Run IVW with error handling
  ivw_res <- tryCatch({
    MendelianRandomization::mr_ivw(mr_input_obj, model = "fixed")
  }, error = function(e) {
    cat("Error in mr_ivw:", e$message, "\n")
    return(NULL)
  })
  
  if (is.null(ivw_res)) {
    cat("Failed to run IVW. Skipping.\n")
    return(NULL)
  }

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

# Before parallel processing, test first pair sequentially
cat("Testing first pair sequentially before parallelization\n")
test_result <- tryCatch({
  run_mr_pair(
    exp_file = pairs_df$exposure_file[1],
    out_file = pairs_df$outcome_file[1],
    pair_idx = 1
  )
}, error = function(e) {
  cat(paste("ERROR in test pair:", e$message, "\n"))
  return(NULL)
})
cat(paste("First pair test complete:", !is.null(test_result), "\n"))

# After your test pair completes
cat("Switching to sequential processing for reliability\n")

# Process pairs sequentially with regular lapply
results_list <- list()
for (i in seq_len(nrow(pairs_df))) {
  cat(sprintf("\nProcessing pair %d of %d\n", i, nrow(pairs_df)))

  result <- tryCatch({
    run_mr_pair(
      exp_file = pairs_df$exposure_file[i],
      out_file = pairs_df$outcome_file[i],
      pair_idx = i
    )
  }, error = function(e) {
    cat(sprintf("ERROR in pair %d: %s\n", i, e$message))
    return(NULL)
  })

  results_list[[i]] <- result

  # Write intermediate results after every 500 pairs
  if (i %% 500 == 0) {
    # Filter out NULL results and combine
    temp_results <- Filter(Negate(is.null), results_list[1:i])
    if (length(temp_results) > 0) {
      temp_df <- do.call(rbind, temp_results)
      # Create temp file name
      temp_file <- paste0(tools::file_path_sans_ext(opt$out_file), "_temp_", i, ".tsv")
      write.table(
        temp_df,
        file = temp_file,
        sep = "\t",
        row.names = FALSE,
        quote = FALSE
      )
      cat(sprintf("Wrote intermediate results (%d pairs) to %s\n", nrow(temp_df), temp_file))
    } else {
      cat("No valid results yet to write intermediate file\n")
    }
  }
}

# 5) Filter out NULL results and combine
results_list <- Filter(Negate(is.null), results_list)

# Check if we have any valid results
if (length(results_list) == 0) {
  cat("\nNo valid results were obtained from any pair!\n")
  # Create an empty results file with header to indicate the script ran
  results_df <- data.frame(
    exposure_file = character(0),
    outcome_file = character(0),
    ivw_estimate = numeric(0),
    ivw_se = numeric(0),
    ivw_pval = numeric(0),
    n_snps = integer(0),
    stringsAsFactors = FALSE
  )
} else {
  results_df <- do.call(rbind, results_list)
  cat("\nAll done! We have", nrow(results_df), "rows of results.\n")
}

# 6) Write final table to the specified out_file
write.table(
  results_df,
  file      = opt$out_file,
  sep       = "\t",
  row.names = FALSE,
  quote     = FALSE
)

cat("Wrote results to:", opt$out_file, "\n")
