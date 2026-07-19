# R dependencies for the Mendelian randomization, colocalization, and
# phenotype-processing scripts in this repository.
#
# Versions pinned below come from the manuscript Methods section. Every other
# package is used in the analysis scripts without a version pin in the
# original code -- confirm the exact version used before submission.
#
# Run this script (or use it as a reference) to install the required
# packages, e.g.:
#   Rscript packages.R

cran_packages <- c(
  "data.table",       # version unspecified -- confirm before submission
  "dplyr",            # version unspecified -- confirm before submission
  "readr",            # version unspecified -- confirm before submission
  "optparse",         # version unspecified -- confirm before submission
  "future.apply",     # version unspecified -- confirm before submission
  "future",           # version unspecified -- confirm before submission
  "purrr",            # version unspecified -- confirm before submission
  "stringr",          # version unspecified -- confirm before submission
  "renv",             # version unspecified -- confirm before submission (only needed if RENV_DIR is set)
  "ggplot2",          # version unspecified -- confirm before submission
  "matrixStats",      # version unspecified -- confirm before submission
  "RhpcBLASctl"        # version unspecified -- confirm before submission
)

bioconductor_packages <- c(
  "preprocessCore"    # version unspecified -- confirm before submission
)

# --- Pinned in the manuscript Methods ---
# MendelianRandomization 0.10.0
# TwoSampleMR 0.6.14
# coloc 5.2.3
# MRPRESSO 1.0
#
# TwoSampleMR and MRPRESSO are distributed from GitHub, not CRAN.

install.packages(setdiff(cran_packages, rownames(installed.packages())))

if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")
BiocManager::install(bioconductor_packages, update = FALSE)

if (!requireNamespace("remotes", quietly = TRUE)) install.packages("remotes")
remotes::install_version("MendelianRandomization", version = "0.10.0")
remotes::install_github("MRCIEU/TwoSampleMR@0.6.14")
remotes::install_version("coloc", version = "5.2.3")
remotes::install_github("rondolab/MR-PRESSO@1.0")
