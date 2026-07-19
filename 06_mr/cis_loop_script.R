#!/usr/bin/env Rscript

# ~~~ PACKAGES ~~~
suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(stringr)
})

# ~~~ USER SETTINGS ~~~
# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR <- "."

# 1) Folder containing the *_gwas_rsids.txt files
input_path  <- file.path(BASE_DIR, "bruna/vcf_gwas_pa/MR_experiment")

# 2) Output folder for the cis-subset files
output_path <- file.path(input_path, "cis_subsets_r2_001")
if (!dir.exists(output_path)) {
  dir.create(output_path, recursive = TRUE)
}

# 3) Path to your offline Ensembl annotation
pos_info_rds <- file.path(BASE_DIR, "bruna/vcf_gwas_pa/MR_experiment/pos_info_all.RDS")

# Load the offline annotation (has columns: hgnc_symbol, chromosome_name, start_position, end_position)
cat("[DEBUG] Loading offline Ensembl coords from:\n  ", pos_info_rds, "\n")
pos_info_all <- readRDS(pos_info_rds)
cat("[DEBUG]", nrow(pos_info_all), "rows in pos_info_all\n")

# ~~~ FIND ALL FILES: Must match "*_gwas_rsids.txt" ~~~
all_files <- list.files(
  path       = input_path,
  pattern    = ".*_gwas_rsids\\.txt$",
  full.names = TRUE
)

cat("[DEBUG] Found", length(all_files), "gwas_rsids.txt files.\n")

# Function to check if a string is all-uppercase
is_all_caps <- function(x) {
  identical(x, toupper(x))
}

# ~~~ LOOP OVER FILES ~~~
for (f in all_files) {
  base_name <- basename(f)  # e.g. "APRT_gwas_rsids.txt"
  # Split by underscore
  parts <- strsplit(base_name, "_")[[1]]
  # The "gene symbol" is everything before "_gwas_rsids.txt"
  # Typically the first underscore chunk is the gene, e.g. "APRT"
  gene_symbol <- parts[1]

  # 1) Check if we skip:
  #    - not uppercase
  #    - starts with 'X' or 'PC'
  if (!is_all_caps(gene_symbol)) {
    cat("[SKIP] Not all-caps:", base_name, "\n")
    next
  }
  if (grepl("^X", gene_symbol) || grepl("^PC", gene_symbol)) {
    cat("[SKIP] Gene symbol starts with X/PC:", base_name, "\n")
    next
  }

  cat("\n[INFO] Processing:", base_name,
      "\n  => Gene symbol:", gene_symbol, "\n")

  # 2) Read the GWAS summary stats
  X1 <- read_tsv(f, show_col_types = FALSE)
  # 2b) Filter to only clumped variants (if clumped file exists)
  clumped_file <- file.path(
    file.path(BASE_DIR, "bruna/vcf_gwas_pa/MR_experiment/r2_001"),
    sub("_gwas_rsids\\.txt$", ".clumped", basename(f))
  )
  
  if (!file.exists(clumped_file)) {
    cat("[SKIP] No clumped file for", gene_symbol, "\n")
    next
  }
  
  clumped_df <- read_table(clumped_file, show_col_types = FALSE)
  if (!"SNP" %in% names(clumped_df)) {
    cat("[SKIP] No 'SNP' column in", clumped_file, "\n")
    next
  }
  
  X1 <- X1 %>% filter(ID %in% clumped_df$SNP)
  cat("  => Retained", nrow(X1), "clumped SNPs before cis filtering.\n")
  
  if (nrow(X1) == 0) {
    cat("[SKIP] No SNPs left after clumping for gene:", gene_symbol, "\n")
    next
  }
  # Basic check
  required_cols <- c("CHROM", "POS")
  if (!all(required_cols %in% names(X1))) {
    stop("[ERROR]", base_name, "does not have CHROM, POS columns.")
  }

  # 3) Lookup gene coords from pos_info_all (offline, no biomaRt)
  # Filter pos_info_all where hgnc_symbol == gene_symbol
  pos_info <- subset(pos_info_all, hgnc_symbol == gene_symbol)
  # Filter out non-standard chromosomes
  pos_info <- subset(pos_info, chromosome_name %in% as.character(1:22))

  if (nrow(pos_info) == 0) {
    cat("[SKIP] No standard-chr entry found for gene:", gene_symbol, "\n")
    next
  }

  # If multiple transcripts, just pick first
  pos_info <- pos_info[1, ]
  chr_of_interest <- pos_info$chromosome_name
  start_gene      <- pos_info$start_position
  end_gene        <- pos_info$end_position

  # 4) Define ±500 kb window
  cis_flank <- 500000
  start_cis <- start_gene - cis_flank
  end_cis   <- end_gene + cis_flank

  # 5) Subset X1
  X1_cis <- X1 %>%
    filter(
      CHROM == chr_of_interest,
      POS >= start_cis,
      POS <= end_cis
    )

  cat("  => Found", nrow(X1_cis), "variants in cis window.\n")

  # 6) Write out the cis-subset
  out_file <- file.path(output_path, paste0(gene_symbol, "_cis_subset.tsv"))
  write_tsv(X1_cis, out_file)
  cat("[DONE]", gene_symbol, ": wrote cis subset to:", out_file, "\n")
}

cat("\nAll done.\n")

