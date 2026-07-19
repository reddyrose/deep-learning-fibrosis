#!/usr/bin/env Rscript

# LIB_DIR should point to a custom R library location, if one is needed; leave
# as "." to use the default R library search path.
LIB_DIR <- "."

# Load libraries
if (LIB_DIR != ".") .libPaths(LIB_DIR)
library(readr)
library(dplyr)
library(MRPRESSO)

# ========================================
# PARSE COMMAND LINE ARGUMENTS
# ========================================
args <- commandArgs(trailingOnly = TRUE)

if (length(args) != 4) {
  cat("Usage: Rscript run_mrpresso.R <protein_name> <outcome_name> <protein_dir> <outcome_dir>\n")
  cat("Example: Rscript run_mrpresso.R CTSS GWAS_output.T1_99th_Percentile /path/to/proteins /path/to/outcomes\n")
  quit(status = 1)
}

protein_name <- args[1]
outcome_name <- args[2]
protein_dir <- args[3]
outcome_dir <- args[4]

# RESULTS_SUBDIR is a placeholder -- two copies of this script were found
# with different values here ("MRPRESSO_results" and "MRPRESSO_results_2");
# which one matches your actual results directory could not be determined
# from source alone. Confirm and set this to the correct subdirectory name
# (or export MRPRESSO_RESULTS_SUBDIR before running) before relying on this
# script to find or reproduce existing results.
RESULTS_SUBDIR <- Sys.getenv("MRPRESSO_RESULTS_SUBDIR", unset = "<RESULTS_SUBDIR>")

# Set output directory
output_dir <- file.path(outcome_dir, RESULTS_SUBDIR)
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# ========================================
# FUNCTION TO EXTRACT ALL MR-PRESSO INFO
# ========================================
extract_presso_results <- function(presso_result, exposure, outcome, n_snps) {
  
  results <- list()
  
  # 1. MAIN MR RESULTS
  main_results <- presso_result$`Main MR results`
  results$main <- data.frame(
    exposure = exposure,
    outcome = outcome,
    n_snps = n_snps,
    raw_causal_estimate = main_results[1, "Causal Estimate"],
    raw_se = main_results[1, "Sd"],
    raw_tstat = main_results[1, "T-stat"],
    raw_pvalue = main_results[1, "P-value"],
    outlier_corrected_estimate = ifelse(nrow(main_results) > 1, main_results[2, "Causal Estimate"], NA),
    outlier_corrected_se = ifelse(nrow(main_results) > 1, main_results[2, "Sd"], NA),
    outlier_corrected_tstat = ifelse(nrow(main_results) > 1, main_results[2, "T-stat"], NA),
    outlier_corrected_pvalue = ifelse(nrow(main_results) > 1, main_results[2, "P-value"], NA),
    stringsAsFactors = FALSE
  )
  
  # 2. GLOBAL TEST
  global_test <- presso_result$`MR-PRESSO results`$`Global Test`
  results$global <- data.frame(
    exposure = exposure,
    outcome = outcome,
    global_test_rss = global_test$RSSobs,
    global_test_pvalue = global_test$Pvalue,
    stringsAsFactors = FALSE
  )
  
  # 3. OUTLIER TEST
  outlier_test <- presso_result$`MR-PRESSO results`$`Outlier Test`
  if (!is.null(outlier_test) && is.data.frame(outlier_test) && nrow(outlier_test) > 0) {
    results$outliers <- outlier_test
    results$outliers$exposure <- exposure
    results$outliers$outcome <- outcome
    results$outliers$snp_index <- 1:nrow(outlier_test)
    results$outliers$is_outlier <- ifelse(is.na(outlier_test$Pvalue), FALSE, outlier_test$Pvalue < 0.05)
  } else {
    results$outliers <- data.frame(
      exposure = character(0),
      outcome = character(0),
      snp_index = integer(0),
      RSSobs = numeric(0),
      Pvalue = numeric(0),
      is_outlier = logical(0),
      stringsAsFactors = FALSE
    )
  }
  
  # 4. DISTORTION TEST - ULTRA DEFENSIVE VERSION
  dist_test <- presso_result$`MR-PRESSO results`$`Distortion Test`
  
  # Initialize with defaults
  outliers_str <- "No significant outliers"
  dist_coef_val <- NA_real_
  dist_pval_val <- NA_real_
  
  # Safely extract each value with explicit checks
  tryCatch({
    # Outliers Indices
    outliers_idx <- dist_test$`Outliers Indices`
    if (!is.null(outliers_idx) && length(outliers_idx) > 0 && !all(is.na(outliers_idx))) {
      outliers_str <- paste(as.character(outliers_idx), collapse = ",")
    }
    
    # Distortion Coefficient
    dist_coef <- dist_test$`Distortion Coefficient`
    if (!is.null(dist_coef) && length(dist_coef) > 0 && !all(is.na(dist_coef))) {
      dist_coef_val <- as.numeric(dist_coef[1])
    }
    
    # Distortion P-value
    dist_pval <- dist_test$Pvalue
    if (!is.null(dist_pval) && length(dist_pval) > 0 && !all(is.na(dist_pval))) {
      dist_pval_val <- as.numeric(dist_pval[1])
    }
    
  }, error = function(e) {
    cat("Warning: Distortion test extraction failed, using defaults\n")
  })
  
  # Create data frame with guaranteed length-1 values
  results$distortion <- data.frame(
    exposure = as.character(exposure)[1],
    outcome = as.character(outcome)[1],
    outliers_detected = as.character(outliers_str)[1],
    distortion_coefficient = dist_coef_val,
    distortion_pvalue = dist_pval_val,
    stringsAsFactors = FALSE
  )
  
  return(results)
}

# ========================================
# RUN MR-PRESSO FOR THIS PAIR
# ========================================
cat("\n========================================\n")
cat("MR-PRESSO Analysis\n")
cat("========================================\n")
cat("Protein:", protein_name, "\n")
cat("Outcome:", outcome_name, "\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
cat("========================================\n\n")

start_time <- Sys.time()

tryCatch({
  # Read data
  cat("Reading protein data...\n")
  X1 <- read_tsv(file.path(protein_dir, paste0(protein_name, "_cause_format.txt")), 
                 show_col_types = FALSE)
  
  cat("Reading outcome data...\n")
  X2 <- read_tsv(file.path(outcome_dir, paste0(outcome_name, "_cause_format.txt")), 
                 show_col_types = FALSE)
  
  # Merge and harmonize
  cat("Harmonizing data...\n")
  dat <- inner_join(X1, X2, by = "snp", suffix = c("_exp", "_out")) %>%
    mutate(
      flip = (A1_exp != A1_out),
      beta_out_harm = ifelse(flip, -beta_hat_out, beta_hat_out)
    )
  
  n_snps <- nrow(dat)
  cat("SNPs available:", n_snps, "\n\n")
  
  if (n_snps < 3) {
    cat("ERROR: Too few SNPs (<3). Cannot run MR-PRESSO.\n")
    quit(status = 1)
  }
  
  # Prepare MR-PRESSO data
  presso_data <- data.frame(
    BetaExposure = dat$beta_hat_exp,
    BetaOutcome = dat$beta_out_harm,
    SdExposure = dat$seb_exp,
    SdOutcome = dat$seb_out
  )
  
  # Run MR-PRESSO
  cat("Running MR-PRESSO (5000 permutations)...\n")
  presso_result <- mr_presso(
    BetaOutcome = "BetaOutcome",
    BetaExposure = "BetaExposure",
    SdOutcome = "SdOutcome",
    SdExposure = "SdExposure",
    OUTLIERtest = TRUE,
    DISTORTIONtest = TRUE,
    data = presso_data,
    NbDistribution = 5000,
    SignifThreshold = 0.05
  )
  
  cat("MR-PRESSO completed successfully!\n\n")
  
  # Save full R object
  pair_prefix <- paste0(protein_name, "_", outcome_name)
  saveRDS(presso_result, 
          file.path(output_dir, paste0(pair_prefix, "_presso_full.rds")))
  
  # Extract all results
  cat("Extracting results...\n")
  results <- extract_presso_results(presso_result, protein_name, outcome_name, n_snps)
  
  # Identify outlier SNPs
  if (nrow(results$outliers) > 0 && any(results$outliers$is_outlier)) {
    outlier_indices <- which(results$outliers$is_outlier)
    outlier_snps <- dat$snp[outlier_indices]
    results$outlier_snps <- data.frame(
      exposure = protein_name,
      outcome = outcome_name,
      snp = outlier_snps,
      snp_index = outlier_indices,
      stringsAsFactors = FALSE
    )
    cat("Outlier SNPs detected:", length(outlier_snps), "\n")
    cat(paste(outlier_snps, collapse = ", "), "\n\n")
  } else {
    results$outlier_snps <- data.frame(
      exposure = character(),
      outcome = character(),
      snp = character(),
      snp_index = integer(),
      stringsAsFactors = FALSE
    )
    cat("No outlier SNPs detected\n\n")
  }
  
  # Save outputs
  cat("Saving results...\n")
  
  # Save input data
  saveRDS(dat, 
          file.path(output_dir, paste0(pair_prefix, "_input_data.rds")))
  
  # Save extracted results as CSV
  write_csv(results$main, 
            file.path(output_dir, paste0(pair_prefix, "_main_results.csv")))
  write_csv(results$global, 
            file.path(output_dir, paste0(pair_prefix, "_global_test.csv")))
  write_csv(results$outliers, 
            file.path(output_dir, paste0(pair_prefix, "_outlier_test.csv")))
  write_csv(results$distortion, 
            file.path(output_dir, paste0(pair_prefix, "_distortion_test.csv")))
  if (nrow(results$outlier_snps) > 0) {
    write_csv(results$outlier_snps, 
              file.path(output_dir, paste0(pair_prefix, "_outlier_snps.csv")))
  }
  
  # Print summary
  end_time <- Sys.time()
  elapsed <- as.numeric(difftime(end_time, start_time, units = "mins"))
  
  cat("\n========================================\n")
  cat("SUMMARY\n")
  cat("========================================\n")
  cat("Raw causal estimate:", round(results$main$raw_causal_estimate, 4), "\n")
  cat("Raw p-value:", format.pval(results$main$raw_pvalue, digits = 3), "\n")
  cat("Global test p-value:", format.pval(results$global$global_test_pvalue, digits = 3), "\n")
  
  if (!is.na(results$main$outlier_corrected_pvalue)) {
    cat("Outlier-corrected estimate:", round(results$main$outlier_corrected_estimate, 4), "\n")
    cat("Outlier-corrected p-value:", format.pval(results$main$outlier_corrected_pvalue, digits = 3), "\n")
  }
  
  cat("\nTime elapsed:", round(elapsed, 2), "minutes\n")
  cat("Results saved to:", output_dir, "\n")
  cat("========================================\n")
  
  cat("\nSUCCESS: Analysis completed\n")
  
}, error = function(e) {
  cat("\n========================================\n")
  cat("ERROR\n")
  cat("========================================\n")
  cat("Message:", conditionMessage(e), "\n")
  cat("========================================\n")
  quit(status = 1)
})
