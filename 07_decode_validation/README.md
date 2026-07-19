# 07_decode_validation

Format conversion for external MR replication in the deCODE Genetics proteomics cohort (Eldjarn et al., *Nature* 2023). Converts deCODE's summary-statistic format into the same UKBB/plink2-style format used elsewhere in this pipeline, so the deCODE data can be run through `06_mr/`'s existing MR scripts. The MR run itself, and the comparison of deCODE vs. UK Biobank MR results, are performed with `06_mr/`'s scripts against the converted inputs.

## Files

Two independent implementations of the same conversion task, kept as alternates.

### `transform_decode_to_ukbb_gwas.py`
Chunked pandas-based converter, suited to large files.
- **Input:** a deCODE summary-stats file (or glob pattern for batch mode), whitespace-delimited with columns `Chrom, Pos, rsids, otherAllele, effectAllele, ImpMAF, N, Beta, SE, minus_log10_pval, Pval`. Filenames must match the pattern `NNNN_NN_GENE_GENE.txt` so the gene name can be extracted.
- **Output:** `<gene>_gwas_rsids.txt` per protein (`CHROM, POS, ID, REF, ALT, A1FREQ, INFO, N, TEST, BETA, SE, CHISQ, LOG10P, EXTRA, P`) -- this naming matches what `06_mr/cis_loop_script.R` expects as input for cis-pQTL extraction.
- **Run:** `python transform_decode_to_ukbb_gwas.py <input_file> <output_dir> [chunksize]` (single file), or `python transform_decode_to_ukbb_gwas.py '*.txt' <output_dir> [chunksize]` (batch/glob mode). `chunksize` defaults to 100000.

### `transform_format_decode.sh`
A lighter awk-based alternative, with a different fixed 12-column positional input schema (`chrom, pos, name, rsids, effectAllele, otherAllele, beta, pval, log10p, se, n, maf`) than the Python script assumes.
- **Output:** `<input_basename>_merged.txt.gz` per input file (`CHROM GENPOS ID ALLELE0 ALLELE1 A1FREQ INFO N TEST BETA SE CHISQ LOG10P EXTRA`); skips files whose output already exists.
- **Run:** `bash transform_format_decode.sh` from within a directory of deCODE `.txt` files.
