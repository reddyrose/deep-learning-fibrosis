#!/usr/bin/env Rscript
##  run_chunk.R  – process up to 15 pairs per task
suppressPackageStartupMessages({
  library(readr); library(dplyr)
  library(MendelianRandomization); library(TwoSampleMR)
  ## add renv activation or .libPaths(...) if you need it
})

## ---- settings -------------------------------------------------------
chunk_size <- 15           # <‑‑ tweak here if you want a different block size

## ---- task index -----------------------------------------------------
task_id <- as.integer(Sys.getenv("SLURM_ARRAY_TASK_ID", "1"))
if (is.na(task_id) || task_id < 1)
  stop("Need positive SLURM_ARRAY_TASK_ID")

## ---- load master list ----------------------------------------------
pairs_df <- read_tsv("pair_list.tsv", show_col_types = FALSE)
n_total  <- nrow(pairs_df)

start_idx <- (task_id - 1) * chunk_size + 1
end_idx   <- min(start_idx + chunk_size - 1, n_total)

if (start_idx > n_total) quit(save="no")   # nothing to do

## ---- source MR helper ----------------------------------------------
source("run_mr_core.R")     # contains run_mr_pair()

## ---- loop over this chunk ------------------------------------------
for (idx in start_idx:end_idx) {

  pair <- pairs_df[idx, ]

  res <- run_mr_pair(
           exp_file = pair$exposure_file,
           out_file = pair$outcome_file,
           pair_idx = idx
         )

  if (!is.null(res)) {
    write.table(res,
      file      = "MR_results.tsv",
      sep       = "\t",
      row.names = FALSE,
      quote     = FALSE,
      col.names = !file.exists("MR_results.tsv"),
      append    = TRUE)
  }
}

