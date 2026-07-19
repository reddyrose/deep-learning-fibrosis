#!/usr/bin/env Rscript

# RENV_DIR should point to an renv project directory, if one is needed; leave
# as "." to skip renv activation and use the default R library search path.
RENV_DIR <- "."

# Prepend your renv library path so these packages are found first.
if (RENV_DIR != ".") {
  .libPaths(c(file.path(RENV_DIR, "renv/library/linux-centos-7/R-4.4/x86_64-pc-linux-gnu/"), .libPaths()))
}

suppressPackageStartupMessages({
  library(renv)
  if (RENV_DIR != ".") renv::activate(RENV_DIR)

  library(optparse)
  library(readr)
})

## --- command‑line options (same names as in MR_job_2.R) --------------
opt <- OptionParser(option_list = list(
  make_option("--protein_roots", type = "character"),
  make_option("--brain_path",    type = "character"),
  make_option("--out_file",      type = "character", default = "pair_list.tsv")
)) |>
  parse_args()

## --- replicate the file‑collection logic -----------------------------
protein_roots <- strsplit(opt$protein_roots, ",")[[1]] |> trimws()

pqtl_files  <- unlist(lapply(
  protein_roots,
  list.files,
  pattern    = "_cis_subset\\.tsv$",
  full.names = TRUE
))
brain_files <- list.files(
  path       = opt$brain_path,
  pattern    = "gwas_rsids\\.txt$",
  full.names = TRUE
)

pairs_df <- expand.grid(
  exposure_file = pqtl_files,
  outcome_file  = brain_files,
  stringsAsFactors = FALSE
)

write_tsv(pairs_df, opt$out_file)
cat("✅  Wrote", nrow(pairs_df), "pairs to", opt$out_file, "\n")

