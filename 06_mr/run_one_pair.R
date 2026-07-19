#!/usr/bin/env Rscript

# ── 0.  Point to your renv library (if you have one) ────────────────
# RENV_DIR should point to an renv project directory, if one is needed; leave
# as "." to skip renv activation and use the default R library search path.
RENV_DIR <- "."
if (RENV_DIR != ".") {
  .libPaths(c(file.path(RENV_DIR, "renv/library/linux-centos-7/R-4.4/x86_64-pc-linux-gnu"),
              .libPaths()))
}
suppressPackageStartupMessages({
  library(renv)
  if (RENV_DIR != ".") renv::activate(RENV_DIR)

  library(readr)
  library(dplyr)
  library(MendelianRandomization)
  library(TwoSampleMR)
})

# Keep every R session single‑threaded on Sherlock
Sys.setenv(OMP_NUM_THREADS        = 1,
           OPENBLAS_NUM_THREADS   = 1,
           MKL_NUM_THREADS        = 1,
           VECLIB_MAXIMUM_THREADS = 1)

# ── 1.  Read the pair index supplied by SLURM_ARRAY_TASK_ID ──────────
pair_idx <- as.integer(commandArgs(trailingOnly = TRUE)[1])
if (is.na(pair_idx) || pair_idx < 1)
  stop("Need a positive numeric pair index!")

# ── 2.  Load master list and pick this row ───────────────────────────
pairs_df <- read_tsv("pair_list.tsv", show_col_types = FALSE)
if (pair_idx > nrow(pairs_df))
  stop("Index ", pair_idx, " is out of range (max = ", nrow(pairs_df), ")")

this_pair <- pairs_df[pair_idx, ]

# ── 3.  Source the function that runs one MR analysis ────────────────
source("run_mr_core.R")   # <- contains run_mr_pair()

# ── 4.  Run it and append result if successful ───────────────────────
res <- run_mr_pair(
         exp_file = this_pair$exposure_file,
         out_file = this_pair$outcome_file,
         pair_idx = pair_idx
       )

if (!is.null(res)) {
  write.table(res,
              file      = "MR_results.tsv",
              sep       = "\t",
              row.names = FALSE,
              quote     = FALSE,
              col.names = !file.exists("MR_results.tsv"),  # header once
              append    = TRUE)
}

