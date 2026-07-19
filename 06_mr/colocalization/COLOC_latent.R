#!/usr/bin/env Rscript
# coloc_loop.R  (2025‑04‑16)

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# LIB_DIR should point to a custom R library location, if one is needed; leave
# as "." to use the default R library search path.
BASE_DIR <- "."
LIB_DIR  <- "."

if (LIB_DIR != ".") .libPaths(c(LIB_DIR, .libPaths()))

suppressPackageStartupMessages({
  library(data.table)
  library(dplyr)
  library(coloc)
  library(RhpcBLASctl)    # pin BLAS/OpenMP
})

##------------------------------------------------------------------
## 0.  USER EDITABLE PATHS
##------------------------------------------------------------------
mr_table      <- file.path(BASE_DIR, "shriya/MR_experiment/completed_MR_2_latent/significant_associations.txt")
cis_root      <- file.path(BASE_DIR, "shriya/all_protiens_cispQTL")
gwas_root     <- file.path(BASE_DIR, "shriya/SHMOLLI_hg38_converted_GWASs/latent_dimensions_HHregressed")
ref_maf_path  <- file.path(BASE_DIR, "bruna/1000G/ref.frq")

pqtl_N        <- 5e4          # protein cohort sample size
p_thr         <- 0.00005         # MR significance
min_shared    <- 20           # min overlap for coloc

##------------------------------------------------------------------
## 1.  ENV & SAFETY
##------------------------------------------------------------------
RhpcBLASctl::blas_set_num_threads(1)
RhpcBLASctl::omp_set_num_threads(1)

if (!interactive()) options(
  error = function() {
    cat("❌  ", geterrmessage(), "\n", file = stderr())
    quit(save = "no", status = 1)
  })

start_time <- Sys.time()

##------------------------------------------------------------------
## 2.  HELPERS
##------------------------------------------------------------------
find_file <- function(root, fname) {
  exact <- file.path(root, fname)
  if (file.exists(exact)) return(exact)
  # allow .gz variants
  gz     <- Sys.glob(file.path(root, "**", paste0(fname, ".gz")))
  plain  <- Sys.glob(file.path(root, "**", fname))
  hit    <- c(plain, gz)[1]
  if (length(hit)) hit else NA_character_
}

std_snp <- function(dt, chr = NULL, pos = NULL, ref = NULL, alt = NULL, rs = NULL) {
  if (!is.null(rs) && rs %in% names(dt)) {
    dt$snp <- dt[[rs]]
  } else if (all(c(chr, pos, ref, alt) %in% names(dt))) {
    dt$snp <- paste0(dt[[chr]], ":", dt[[pos]], "_", dt[[ref]], "_", dt[[alt]])
  } else stop("Cannot create SNP identifier.")
  dt
}

##------------------------------------------------------------------
## 3.  LOAD STATIC TABLES
##------------------------------------------------------------------
ref_maf <- fread(ref_maf_path, select = c("SNP", "MAF"))

mr_hits_all <- fread(mr_table)
if (!"IVW_PVAL" %in% toupper(names(mr_hits_all)))
  stop("Column 'ivw_pval' (any case) not found in MR table")

colnames(mr_hits_all) <- toupper(colnames(mr_hits_all))
mr_hits <- mr_hits_all %>% filter(IVW_PVAL < p_thr)

cat("📝  total MR‑significant pairs =", nrow(mr_hits), "\n")

##------------------------------------------------------------------
## 4.  SLURM ARRAY CHUNKING
##------------------------------------------------------------------

task_id <- as.integer(Sys.getenv("SLURM_ARRAY_TASK_ID",  "1"))
n_tasks <- as.integer(Sys.getenv("SLURM_ARRAY_TASK_COUNT", "1"))

# clamp to 1…nrow
n_tasks <- max(1, min(n_tasks, nrow(mr_hits)))

if (n_tasks == 1) {
  chunks <- list(mr_hits)               # whole table in one chunk
} else {
  # cut() works only when n_tasks ≥ 2
  chunks <- split(mr_hits,
                  cut(seq_len(nrow(mr_hits)), n_tasks, labels = FALSE))
}

my_hits <- chunks[[min(task_id, length(chunks))]]


cat("🗂️   task", task_id, "processing", nrow(my_hits), "pairs\n")

##------------------------------------------------------------------
## 5.  MAIN LOOP
##------------------------------------------------------------------
gwas_cache <- new.env(parent = emptyenv())
out        <- list()
miss_file  <- 0
few_snps   <- 0
example_prot <- trimws(my_hits$EXPOSURE_FILE[1])
example_gwas <- trimws(my_hits$OUTCOME_FILE[1])

cat(find_file(cis_root,  example_prot), "\n")
cat(find_file(gwas_root, example_gwas), "\n")

# return the (first) column that exists, otherwise NA_real_
pick_col <- function(tbl, candidates) {
  hit <- intersect(candidates, names(tbl))
  if (length(hit)) tbl[[ hit[1] ]] else NA_real_
}

pick_col2 <- function(tbl, candidates) {   # returns vector
  unlist(pick_col(tbl, candidates))
}

pick_num <- function(tbl, candidates, fun = max) {
  hit <- intersect(candidates, names(tbl))
  if (length(hit)) fun(tbl[[hit[1]]], na.rm = TRUE) else NA_real_
}

for (ii in seq_len(nrow(my_hits))) {
  
  prot_file <- trimws(my_hits$EXPOSURE_FILE[ii])
  gwas_file <- trimws(my_hits$OUTCOME_FILE[ii])
  
  prot_path <- find_file(cis_root,  prot_file)
  gwas_path <- find_file(gwas_root, gwas_file)
  
  if (is.na(prot_path) || is.na(gwas_path)) {
    miss_file <- miss_file + 1
    next
  }
  
  if (!exists(gwas_path, envir = gwas_cache)) {
    cat("📥  GWAS:", basename(gwas_path), "\n")
    gw <- fread(gwas_path)
    names(gw) <- toupper(names(gw))
    gw <- std_snp(gw, chr="CHR", pos="POS", ref="REF", alt="ALT", rs="SNP") %>%
      transmute(
        snp     = snp,
        beta    = pick_col2(., c("BETA", "EFFECT", "BETA_HAT")),
        varbeta = pick_col2(., c("SE",   "STDERR"))^2,
        N       = pick_num(., c("OBS_CT", "N", "TOTALSAMPLES"))
      ) %>%
      left_join(ref_maf, by = c("snp" = "SNP"))
    
    assign(gwas_path, gw, envir = gwas_cache)
  }
  gwas <- get(gwas_path, envir = gwas_cache)
  
  pq  <- fread(prot_path)
  names(pq) <- toupper(names(pq))
  pq <- std_snp(pq, rs = "ID") %>%
    transmute(
      snp     = snp,
      beta    = pick_col2(., c("BETA", "EFFECT")),
      varbeta = pick_col2(., c("SE",   "STDERR"))^2,
      N       = pqtl_N
    ) %>%
    left_join(ref_maf, by = c("snp" = "SNP"))
  
  shared <- intersect(pq$snp, gwas$snp)
  if (length(shared) < min_shared) {
    few_snps <- few_snps + 1
    next
  }
  
  d1 <- pq   %>% filter(snp %in% shared)
  d2 <- gwas %>% filter(snp %in% shared)
  
  dataset1 <- list(
    snp      = d1$snp,
    beta     = d1$beta,
    varbeta  = d1$varbeta,
    MAF      = d1$MAF,
    N        = d1$N[1],
    type     = "quant"
  )
  
  dataset2 <- list(
    snp      = d2$snp,
    beta     = d2$beta,
    varbeta  = d2$varbeta,
    MAF      = d2$MAF,
    N        = d2$N[1],
    type     = "quant"
  )
  
  coloc_out <- coloc.abf(dataset1, dataset2)
  
  out[[length(out)+1]] <-
    data.table(exposure = sub("_cis_subset\\.tsv$", "", basename(prot_file)),
               outcome  = basename(gwas_path),
               pp_h4    = coloc_out$summary["PP.H4.abf"],
               pp_h3    = coloc_out$summary["PP.H3.abf"],
               n_snps   = length(shared))
}

##------------------------------------------------------------------
## 6.  WRITE RESULT + SUMMARY
##------------------------------------------------------------------
tag <- sprintf("task%02d_of%02d", task_id, n_tasks)
outfile <- sprintf("coloc_results_latent_%s.tsv.gz", tag)

if (length(out)) {
  fwrite(rbindlist(out), outfile)
  cat("✅  wrote", outfile, "\n")
} else {
  cat("⚠️   no coloc run for this task\n")
}

cat(sprintf("⏱️  done in %s — missing:%d  <50SNP:%d\n",
            format(Sys.time() - start_time), miss_file, few_snps))
