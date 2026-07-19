#!/usr/bin/env Rscript
# ---- 0)   Load libs & pin ALL threads to 1 --------------------------
# RENV_DIR should point to an renv project directory, if one is needed; leave
# as "." to skip and use the default R library search path.
RENV_DIR <- "."
if (RENV_DIR != ".") {
  .libPaths(c(file.path(RENV_DIR, "renv/library/linux-centos-7/R-4.4/x86_64-pc-linux-gnu/"),
              .libPaths()))
}

suppressPackageStartupMessages({
  library(RhpcBLASctl)
  library(MendelianRandomization)
  library(TwoSampleMR)
  library(readr)
  library(dplyr)
  library(data.table)
  library(future.apply)
})

# one thread for everything
blas_set_num_threads(1L)
omp_set_num_threads(1L)
Sys.setenv(OMP_NUM_THREADS        = 1,
           OPENBLAS_NUM_THREADS   = 1,
           MKL_NUM_THREADS        = 1,
           VECLIB_MAXIMUM_THREADS = 1)
data.table::setDTthreads(1)

# ---- 1)   Load helper & pair list -----------------------------------
source("run_mr_core.R")                   # contains run_mr_pair()
#pairs_df <- read_tsv("pair_list.tsv", show_col_types = FALSE)
pairs_df <- fread("pair_list.tsv", sep = "\t", data.table = FALSE)
cat("Total pairs:", nrow(pairs_df), "\n")

# ---- 2)   Set exactly FIVE workers ----------------------------------
plan(multisession, workers = 5)
## ---- re‑pin BLAS/OMP threads inside every worker (old‑future friendly) ----
if ("future" %in% loadedNamespaces()) {
  cl <- future:::ClusterRegistry("get")   # returns current worker cluster
  if (length(cl)) {
    parallel::clusterCall(cl, function() {
      RhpcBLASctl::blas_set_num_threads(1L)
      RhpcBLASctl::omp_set_num_threads(1L)
      data.table::setDTthreads(1)
    })
  }
}
# ---- 3)   Run everything in parallel --------------------------------
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

# ---- 4)   Combine & write -------------------------------------------
results_df <- data.table::rbindlist(Filter(Negate(is.null), results_list),
                                    use.names = TRUE, fill = TRUE)
fwrite(results_df, "MR_results.tsv", sep = "\t")
cat("✅  Wrote", nrow(results_df), "rows to MR_results.tsv\n")

