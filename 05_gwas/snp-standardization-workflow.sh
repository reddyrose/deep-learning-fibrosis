#!/usr/bin/bash
#SBATCH --job-name=KGWAS_standardize
#SBATCH --time=20:00:00
#SBATCH --partition=euan
#SBATCH --mem=20G  # Memory limit
#SBATCH --nodes=1 # Number of nodes
#SBATCH --ntasks=1 # Number of tasks
#SBATCH --cpus-per-task=8


# Workflow for standardizing SNP IDs from GWAS summary statistics
# This script standardizes a mix of CHR:POS:REF:ALT and rs IDs to a consistent format


# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."

export VEP_CONTAINER="${BASE_DIR}/shriya/containers/ensembl-vep_latest.sif"


# Define paths and directories
INPUT_DIR="${BASE_DIR}/shriya/kgwas_outputs/gwas_inputs_formatted"
OUTPUT_DIR="${BASE_DIR}/shriya/kgwas_outputs/gwas_inputs_standardized"
VEP_CONTAINER="${BASE_DIR}/shriya/containers/ensembl-vep_latest.sif"  # Update this path to your VEP container

# Create output directory if it doesn't exist
mkdir -p $OUTPUT_DIR

# Process each GWAS file in the input directory
for INPUT_FILE in $INPUT_DIR/*.{txt,tsv,gz}; do
    # Skip if no files match the pattern
    [ -e "$INPUT_FILE" ] || continue
    
    # Get the base filename without extension
    FILENAME=$(basename "$INPUT_FILE")
    BASENAME=${FILENAME%.*}
    
    echo "Processing $FILENAME..."
    
    # Create a temporary directory for processing this file
    TEMP_DIR="${OUTPUT_DIR}/temp_${BASENAME}"
    mkdir -p $TEMP_DIR
    
    # If file is gzipped, uncompress it to temp directory
    if [[ "$INPUT_FILE" == *.gz ]]; then
        gunzip -c "$INPUT_FILE" > "${TEMP_DIR}/input.txt"
        WORKING_FILE="${TEMP_DIR}/input.txt"
    else
        WORKING_FILE="$INPUT_FILE"
    fi
    
    # Extract header
    head -1 "$WORKING_FILE" > "${TEMP_DIR}/header.txt"
    
    # Extract SNPs that are not in rs ID format (CHR:POS:REF:ALT format)
    awk 'NR>1 && $3 !~ /^rs/ {print $1"\t"$2"\t"$3"\t"$4"\t"$5}' "$WORKING_FILE" > "${TEMP_DIR}/non_rs_snps.txt"
    
    # Convert to VEP input format (chr pos ref alt format)
    # VEP expects tab-delimited: chromosome, start, end, allele, strand
    awk '{split($3,a,":"); print $1"\t"$2"\t"$2"\t"$4"/"$5"\t+"}' "${TEMP_DIR}/non_rs_snps.txt" > "${TEMP_DIR}/vep_input.txt"
    
    # Check if we have SNPs to convert
    if [[ -s "${TEMP_DIR}/vep_input.txt" ]]; then
        echo "Running VEP to convert position-based SNPs to rs IDs..."
        
        # Run VEP to annotate with rs IDs
        singularity exec $VEP_CONTAINER \
        vep --input_file "${TEMP_DIR}/vep_input.txt" \
            --format vcf \
            --output_file "${TEMP_DIR}/vep_output.txt" \
            --force_overwrite \
            --symbol \
            --check_existing \
            --no_stats \
            --cache
            --dir_cache $SCRATCH/vep_cache \
            --species homo_sapiens \
            --assembly GRCh38
            --fork 8
          
        if [ ! -f "${TEMP_DIR}/vep_output.txt" ]; then
            echo "ERROR: VEP output file not found. VEP may have failed to run properly."
            echo "Check that the cache directory exists at: $SCRATCH/vep_cache"
            #  Create empty mapping to avoid further errors
            touch "${TEMP_DIR}/id_mapping.txt"
        fi

        # Extract rs IDs from VEP output and create mapping file
        # Format: original_id rs_id
        grep -v "^#" "${TEMP_DIR}/vep_output.txt" | \
        awk -F'\t' '{
            original_id = $1":"$2":"$3":"$4;
            if ($12 ~ /rs[0-9]+/) {
                match($12, /rs[0-9]+/);
                print original_id"\t"substr($12, RSTART, RLENGTH);
            } else {
                print original_id"\t"original_id;
            }
        }' > "${TEMP_DIR}/id_mapping.txt"
        
        # Create a comprehensive mapping file including rs IDs that were already present
        awk 'NR>1 && $3 ~ /^rs/ {print $3"\t"$3}' "$WORKING_FILE" >> "${TEMP_DIR}/id_mapping.txt"
        
        # Apply mapping to create standardized GWAS file
        # First, write the header
        cat "${TEMP_DIR}/header.txt" > "${OUTPUT_DIR}/${BASENAME}_standardized.txt"
        
        # Then apply mapping to the data rows
        awk 'NR>1' "$WORKING_FILE" | \
        while read -r line; do
            snp_id=$(echo "$line" | awk '{print $3}')
            standardized_id=$(grep -m 1 "^$snp_id" "${TEMP_DIR}/id_mapping.txt" | cut -f2)
            
            # If no mapping found, keep original ID
            if [ -z "$standardized_id" ]; then
                standardized_id="$snp_id"
            fi
            
            # Replace the SNP ID in the line
            echo "$line" | awk -v new_id="$standardized_id" '{$3=new_id; print}' >> "${OUTPUT_DIR}/${BASENAME}_standardized.txt"
        done
        
        echo "Created standardized file: ${OUTPUT_DIR}/${BASENAME}_standardized.txt"
    else
        echo "No position-based SNPs found to convert in $FILENAME"
        cp "$WORKING_FILE" "${OUTPUT_DIR}/${BASENAME}_standardized.txt"
    fi
    
    # Optional: Clean up temporary files
    if [ "$CLEANUP" = "true" ]; then
        rm -rf "$TEMP_DIR"
    fi
done

echo "Standardization workflow completed!"
