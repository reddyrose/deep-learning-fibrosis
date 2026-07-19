#!/bin/bash

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR="."

#Create the destination directory if it doesn't exist
TARGET_DIR="${BASE_DIR}/shriya/SHMOLLI-output-unet-myocardium-update/OG_T1_gwas_files"
mkdir -p "$TARGET_DIR"

# Current directory
SOURCE_DIR="${BASE_DIR}/shriya/t1_myocardium_gwas_sensitivity_analysis/all_pheno"
cd "$SOURCE_DIR"

# Move only the base GWAS files (not the processed vcf or index files)
for file in gwas_output.*.glm.linear; do
    # Skip if the glob fails
    [[ "$file" == "gwas_output.*.glm.linear" ]] && { echo "No matching files found."; break; }
    
    # Skip if supplementary files
    if [[ "$file" == *".adjusted" || "$file" == *".id" || "$file" == *".vcf.gz" || "$file" == *".tbi" ]]; then
        echo "Skipping $file (supplementary file)"
        continue
    fi
    
    # Skip if we've already processed this phenotype
    phenotype=$(echo "$file" | sed -E 's/gwas_output\.(.*?)\.glm\.linear.*/\1/')
    
    # Copy the file
    echo "Copying $file to $TARGET_DIR/"
    cp "$file" "$TARGET_DIR/"
    
    # Also copy the gzipped version if it exists
    if [[ -f "${file}.gz" ]]; then
        echo "Copying ${file}.gz to $TARGET_DIR/"
        cp "${file}.gz" "$TARGET_DIR/"
    fi
done

echo "Files copied to $TARGET_DIR"
echo "You can verify with 'ls -l $TARGET_DIR'"
