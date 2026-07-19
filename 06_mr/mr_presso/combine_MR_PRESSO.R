#!/usr/bin/env Rscript

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# LIB_DIR should point to a custom R library location, if one is needed; leave
# as "." to use the default R library search path.
BASE_DIR <- "."
LIB_DIR  <- "."

if (LIB_DIR != ".") .libPaths(LIB_DIR)

library(readr)
library(dplyr)
library(purrr)

# RESULTS_SUBDIR is a placeholder -- see run_MR_PRESSO.R for why the exact
# subdirectory name is unconfirmed. Keep this in sync with whatever
# RESULTS_SUBDIR (or $MRPRESSO_RESULTS_SUBDIR) run_MR_PRESSO.R actually wrote
# results to, or this script will silently find nothing.
RESULTS_SUBDIR <- Sys.getenv("MRPRESSO_RESULTS_SUBDIR", unset = "<RESULTS_SUBDIR>")
output_dir <- file.path(BASE_DIR, "shriya/CAUSE_gwas_summary_stats", RESULTS_SUBDIR)

cat("Combining MR-PRESSO results...\n")

# List all result files
main_files <- list.files(output_dir, pattern = "*_main_results.csv", full.names = TRUE)
global_files <- list.files(output_dir, pattern = "*_global_test.csv", full.names = TRUE)
distortion_files <- list.files(output_dir, pattern = "*_distortion_test.csv", full.names = TRUE)

cat("Found", length(main_files), "completed analyses\n\n")

# Function to read and clean p-values and outliers
read_and_clean <- function(file) {
  df <- read_csv(file, show_col_types = FALSE, col_types = cols(.default = "c"))
  
  # Convert numeric columns back to numeric (except outliers_detected)
  numeric_cols <- c("n_snps", "raw_causal_estimate", "raw_se", "raw_tstat", "raw_pvalue",
                    "outlier_corrected_estimate", "outlier_corrected_se", 
                    "outlier_corrected_tstat", "outlier_corrected_pvalue",
                    "global_test_rss", "global_test_pvalue",
                    "distortion_coefficient", "distortion_pvalue")
  
  for (col in numeric_cols) {
    if (col %in% names(df)) {
      # Remove "<" from p-values before converting
      df[[col]] <- gsub("<", "", df[[col]])
      df[[col]] <- as.numeric(df[[col]])
    }
  }
  
  # Ensure outliers_detected stays as character
  if ("outliers_detected" %in% names(df)) {
    df$outliers_detected <- as.character(df$outliers_detected)
  }
  
  return(df)
}

# Combine results with cleaning
main_results <- map_dfr(main_files, read_and_clean)
global_results <- map_dfr(global_files, read_and_clean)
distortion_results <- map_dfr(distortion_files, read_and_clean)

# Create summary
summary_df <- main_results %>%
  left_join(global_results, by = c("exposure", "outcome")) %>%
  left_join(distortion_results, by = c("exposure", "outcome")) %>%
  mutate(
    significant_raw = raw_pvalue < 0.05,
    significant_pleiotropy = global_test_pvalue < 0.05,
    outliers_removed = !is.na(outlier_corrected_pvalue),
    significant_corrected = ifelse(outliers_removed, 
                                    outlier_corrected_pvalue < 0.05, 
                                    NA),
    quality_flag = case_when(
      !significant_raw ~ "Not significant",
      significant_raw & !significant_pleiotropy ~ "Pass: No pleiotropy",
      significant_raw & significant_pleiotropy & outliers_removed & significant_corrected ~ 
        "Pass: Significant after correction",
      significant_raw & significant_pleiotropy & outliers_removed & !significant_corrected ~ 
        "Fail: Non-significant after correction",
      significant_raw & significant_pleiotropy & !outliers_removed ~ 
        "Caution: Pleiotropy but no outliers",
      TRUE ~ "Unknown"
    )
  ) %>%
  arrange(raw_pvalue)

# Save combined results
write_csv(summary_df, file.path(output_dir, "mrpresso_all_results_summary.csv"))
write_csv(main_results, file.path(output_dir, "mrpresso_all_main_results.csv"))
write_csv(global_results, file.path(output_dir, "mrpresso_all_global_tests.csv"))

cat("Summary Statistics:\n")
cat("==================\n")
cat("Total pairs:", nrow(summary_df), "\n")
cat("Significant raw effects:", sum(summary_df$significant_raw, na.rm = TRUE), "\n")
cat("Significant pleiotropy:", sum(summary_df$significant_pleiotropy, na.rm = TRUE), "\n\n")

cat("Quality Flags:\n")
print(table(summary_df$quality_flag))

cat("\n\nTop Results by P-value:\n")
cat("=======================\n")
print(summary_df %>% 
        select(exposure, outcome, n_snps, raw_pvalue, global_test_pvalue, quality_flag) %>%
        head(20), n = 20)

cat("\n\nResults saved to:", output_dir, "\n")
