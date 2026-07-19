#!/usr/bin/env bash
#SBATCH --job-name=gwas_pipeline
#SBATCH --time=48:00:00
#SBATCH --partition=euan
#SBATCH --mem=20G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --output=gwas_pipeline_%j.out
#SBATCH --error=gwas_pipeline_%j.err

# Exit on error and enable debugging
set -e
set -x

# Load required modules
ml load biology
ml bcftools/1.16

# NOTE:  NEED TO MANUALLY ACTIVATE CROSSMAP

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."

# Define paths
CHAIN_FILE="${BASE_DIR}/shriya/hg19ToHg38.over.chain.gz"
REFERENCE_GENOME="${BASE_DIR}/shriya/GRCh38.fa"
INPUT_DIR="${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update2/VAE_GWAS"
FINAL_OUTPUT_DIR="${BASE_DIR}/shriya/SHMOLLI_hg38_converted_GWASs/latent_dimensions_HHregressed"
DBSNP_FILE="${BASE_DIR}/shriya/vcf/00-All.vcf.gz"

# Create output directory
mkdir -p "$FINAL_OUTPUT_DIR"

# Change to input directory
cd "$INPUT_DIR"

echo "Starting GWAS processing pipeline..."
echo "======================================"

# Process each .glm.linear.gz file (we'll adapt for uncompressed files as well)
for linear_file in *.glm.linear*; do
    # Skip if no files found
    [[ "$linear_file" == "*.glm.linear*" || ! -e "$linear_file" ]] && { echo "No .glm.linear files found."; break; }
    
    # Skip files that end with .adjusted or .id
    if [[ "$linear_file" == *".adjusted" || "$linear_file" == *".id" ]]; then
        echo "Skipping $linear_file (appears to be a supplementary file)"
        continue
    fi

    # Only process Latent_7, Latent_8, and Latent_9
    #if [[ "$linear_file" != *"Latent_7"* && "$linear_file" != *"Latent_8"* && "$linear_file" != *"Latent_9"* ]]; then
    #    echo "Skipping $linear_file (not one of the target latent phenotypes)"
    #    continue
    #fi
    
    echo "======================================================="
    echo "Processing: $linear_file"
    echo "======================================================="
    
    # Extract phenotype name from filename
    if [[ "$linear_file" == gwas_output.* ]]; then
        phenotype=$(echo "$linear_file" | sed -E 's/gwas_output\.(.*?)\.glm\.linear.*/\1/')
    elif [[ "$linear_file" == gwas_PC3_output.* ]]; then
        phenotype=$(echo "$linear_file" | sed -E 's/gwas_PC3_output\.(.*?)\.glm\.linear.*/PC3_\1/')
    else
        phenotype=$(echo "$linear_file" | sed -E 's/(.*?)\.glm\.linear.*/\1/')
    fi
    
    echo "Identified phenotype: $phenotype"
    
    # Create temporary directory for this file
    TMP_DIR=$(mktemp -d)
    
    echo "Step 1: Converting GWAS to VCF format for phenotype: $phenotype"
    
    # Create VCF header
    cat <<EOF > "$TMP_DIR/header.txt"
##fileformat=VCFv4.2
##INFO=<ID=A1,Number=1,Type=String,Description="Allele used in effect estimation">
##INFO=<ID=TEST,Number=1,Type=String,Description="Model used in the GWAS (e.g. ADD)">
##INFO=<ID=OBS_CT,Number=1,Type=Integer,Description="Sample size for this association">
##INFO=<ID=BETA,Number=1,Type=Float,Description="Effect size estimate">
##INFO=<ID=SE,Number=1,Type=Float,Description="Standard error of the effect size">
##INFO=<ID=T_STAT,Number=1,Type=Float,Description="T-statistic for the effect">
##INFO=<ID=P,Number=1,Type=Float,Description="P-value for the association">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
EOF

    # Check if file is compressed or uncompressed
    if [[ "$linear_file" == *.gz ]]; then
        # Compressed file - use zcat
        zcat "$linear_file" | head -1 > "$TMP_DIR/header_check.txt"
    else
        # Uncompressed file - use head directly
        head -1 "$linear_file" > "$TMP_DIR/header_check.txt"
    fi
    
    if grep -q "#CHROM" "$TMP_DIR/header_check.txt"; then
        # File already has VCF-like header
        echo "File appears to have VCF-like header"
        
        # Convert to VCF body 
        if [[ "$linear_file" == *.gz ]]; then
            zcat "$linear_file" | awk 'NR>1 {
              info_str = sprintf("A1=%s;TEST=%s;OBS_CT=%s;BETA=%s;SE=%s;T_STAT=%s;P=%s",
                                 $6, $7, $8, $9, $10, $11, $12)
              printf("%s\t%s\t%s\t%s\t%s\t.\t.\t%s\n",
                     $1, $2, $3, $4, $5, info_str)
            }' > "$TMP_DIR/body.txt"
        else
            awk 'NR>1 {
              info_str = sprintf("A1=%s;TEST=%s;OBS_CT=%s;BETA=%s;SE=%s;T_STAT=%s;P=%s",
                                 $6, $7, $8, $9, $10, $11, $12)
              printf("%s\t%s\t%s\t%s\t%s\t.\t.\t%s\n",
                     $1, $2, $3, $4, $5, info_str)
            }' "$linear_file" > "$TMP_DIR/body.txt"
        fi
    else
        # Try to detect column structure
        echo "Detecting column structure..."
        
        if [[ "$linear_file" == *.gz ]]; then
            header_line=$(zcat "$linear_file" | head -1)
        else
            header_line=$(head -1 "$linear_file")
        fi
        
        echo "Header: $header_line"
        
        # Fall back to default format as a safe option
        echo "Using default column assumptions"
        if [[ "$linear_file" == *.gz ]]; then
            zcat "$linear_file" | awk 'NR>1 && $0 !~ /^#/ {
                info_str = sprintf("A1=%s;TEST=%s;OBS_CT=%s;BETA=%s;SE=%s;T_STAT=%s;P=%s",
                              $6, "ADD", $8, $9, $10, $11, $12);
                printf("%s\t%s\t%s\t%s\t%s\t.\t.\t%s\n",
                     $1, $2, $3, $4, $5, info_str);
            }' > "$TMP_DIR/body.txt"
        else
            awk 'NR>1 && $0 !~ /^#/ {
                info_str = sprintf("A1=%s;TEST=%s;OBS_CT=%s;BETA=%s;SE=%s;T_STAT=%s;P=%s",
                              $6, "ADD", $8, $9, $10, $11, $12);
                printf("%s\t%s\t%s\t%s\t%s\t.\t.\t%s\n",
                     $1, $2, $3, $4, $5, info_str);
            }' "$linear_file" > "$TMP_DIR/body.txt"
        fi
    fi
    
    # Check if body.txt has content
    if [[ ! -s "$TMP_DIR/body.txt" ]]; then
        echo "Warning: Failed to extract data from $linear_file. Skipping to next file."
        rm -rf "$TMP_DIR"
        continue
    fi
    
    # Combine header and body into a VCF
    cat "$TMP_DIR/header.txt" "$TMP_DIR/body.txt" > "$TMP_DIR/temp.vcf"
    
    # Sort the VCF (required for CrossMap and most tools)
    echo "Step 2: Sorting VCF..."
    grep "^#" "$TMP_DIR/temp.vcf" > "$TMP_DIR/header_only.vcf"
    grep -v "^#" "$TMP_DIR/temp.vcf" | sort -k1,1 -k2,2n > "$TMP_DIR/sorted_body.vcf"
    cat "$TMP_DIR/header_only.vcf" "$TMP_DIR/sorted_body.vcf" > "$TMP_DIR/sorted.vcf"
    
    # Compress and index for CrossMap
    bgzip -c "$TMP_DIR/sorted.vcf" > "$TMP_DIR/sorted.vcf.gz"
    tabix -p vcf "$TMP_DIR/sorted.vcf.gz"
    
    echo "Step 2.5: Validating VCF file..."
    bcftools view -H "$TMP_DIR/sorted.vcf.gz" | \
    awk -F'\t' 'NF == 8 {print}' > "$TMP_DIR/validated_body.vcf"

    # Create a new validated VCF
    grep "^#" "$TMP_DIR/sorted.vcf" > "$TMP_DIR/validated.vcf"
    cat "$TMP_DIR/validated_body.vcf" >> "$TMP_DIR/validated.vcf"
    bgzip -c "$TMP_DIR/validated.vcf" > "$TMP_DIR/validated.vcf.gz"
    tabix -p vcf "$TMP_DIR/validated.vcf.gz"

    echo "Step 3: Converting coordinates from hg19 to hg38..."
    
    # Run CrossMap for liftover
    CrossMap vcf "$CHAIN_FILE" "$TMP_DIR/validated.vcf.gz" "$REFERENCE_GENOME" "$TMP_DIR/${phenotype}_hg38.vcf"
    
    echo "Step 4: Fixing and sorting hg38 VCF..."
    
    # Fix the CrossMap output - ensure proper tab-delimiting
    # This addresses the bcftools error with headers
    sed -i 's/ \{1,\}/\t/g' "$TMP_DIR/${phenotype}_hg38.vcf"
    
    # Now sort manually to avoid bcftools issues
    grep "^#" "$TMP_DIR/${phenotype}_hg38.vcf" > "$TMP_DIR/${phenotype}_hg38.header.vcf"
    grep -v "^#" "$TMP_DIR/${phenotype}_hg38.vcf" | sort -k1,1 -k2,2n > "$TMP_DIR/${phenotype}_hg38.sorted_body.vcf"
    cat "$TMP_DIR/${phenotype}_hg38.header.vcf" "$TMP_DIR/${phenotype}_hg38.sorted_body.vcf" > "$TMP_DIR/${phenotype}_hg38.sorted.vcf"
    
    # Compress the sorted hg38 VCF
    bgzip -f "$TMP_DIR/${phenotype}_hg38.sorted.vcf"
    tabix -p vcf "$TMP_DIR/${phenotype}_hg38.sorted.vcf.gz"
    
    echo "Step 5: Annotating variants with dbSNP IDs..."
    
    # Annotate with dbSNP IDs
    bcftools annotate \
      -a "$DBSNP_FILE" \
      -c ID \
      -o "$TMP_DIR/${phenotype}_hg38_annotated.vcf.gz" \
      -O z \
      "$TMP_DIR/${phenotype}_hg38.sorted.vcf.gz"
    
    # Index the annotated file
    tabix -p vcf "$TMP_DIR/${phenotype}_hg38_annotated.vcf.gz"
    
    echo "Step 6: Creating final GWAS text format..."
    
    # Create GWAS text format for easy analysis
    echo -e "CHR\tPOS\tSNP\tREF\tALT\tA1\tTEST\tN\tBETA\tSE\tT_STAT\tP" > "$FINAL_OUTPUT_DIR/${phenotype}_gwas.txt"
    
    # Extract and format data from the annotated VCF
    bcftools query -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%INFO/A1\t%INFO/TEST\t%INFO/OBS_CT\t%INFO/BETA\t%INFO/SE\t%INFO/T_STAT\t%INFO/P\n' \
      "$TMP_DIR/${phenotype}_hg38_annotated.vcf.gz" >> "$FINAL_OUTPUT_DIR/${phenotype}_gwas.txt"
    
    # Copy final VCF file to output directory
    cp "$TMP_DIR/${phenotype}_hg38_annotated.vcf.gz" "$FINAL_OUTPUT_DIR/${phenotype}_hg38_annotated.vcf.gz"
    cp "$TMP_DIR/${phenotype}_hg38_annotated.vcf.gz.tbi" "$FINAL_OUTPUT_DIR/${phenotype}_hg38_annotated.vcf.gz.tbi"
    
    echo "Step 7: Cleaning up temporary files..."
    rm -rf "$TMP_DIR"
    
    echo "Completed processing $linear_file"
    echo "======================================================="
done

echo "All processing complete! Final files are in $FINAL_OUTPUT_DIR"
echo "Tabular GWAS files: *_gwas.txt"
echo "Annotated VCF files: *_hg38_annotated.vcf.gz"
