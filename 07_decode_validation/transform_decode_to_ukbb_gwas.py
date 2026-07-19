#!/usr/bin/env python3
"""
Transform deCODE GWAS summary statistics to UKBB format
MEMORY-EFFICIENT VERSION for large files (processes in chunks)
"""

import pandas as pd
import numpy as np
import sys
import os
import glob
from pathlib import Path

def extract_gene_name(filename):
    """
    Extract gene name from deCODE filename format: NNNN_NN_GENE_GENE.txt
    Returns the gene name
    """
    basename = os.path.basename(filename)
    # Split by underscore and get the third element (gene name)
    parts = basename.replace('.txt', '').split('_')
    if len(parts) >= 3:
        return parts[2]  # Usually the gene name is the 3rd element
    return None

def transform_chunk(chunk_df):
    """
    Transform a chunk of data from deCODE format to UKBB format
    """
    # Create new dataframe with UKBB format columns IN CORRECT ORDER
    df_ukbb = pd.DataFrame()
    
    # Column transformations
    # Remove 'chr' prefix from chromosome
    df_ukbb['CHROM'] = chunk_df['Chrom'].str.replace('chr', '', regex=False)
    df_ukbb['POS'] = chunk_df['Pos']
    
    # Create temporary REF/ALT for ID generation
    # REF/ALT: In GWAS, effectAllele is typically the alternate allele
    # and otherAllele is the reference
    temp_ref = chunk_df['otherAllele']
    temp_alt = chunk_df['effectAllele']
    
    # ID: Use rsID if available, otherwise create positional ID (CHROM:POS:REF:ALT)
    # This must come BEFORE REF/ALT in the final column order
    temp_id = chunk_df['rsids'].fillna('NA')  # First fill with 'NA' string
    missing_rsid = (temp_id == 'NA') | (temp_id == '.')
    temp_id.loc[missing_rsid] = (
        df_ukbb.loc[missing_rsid, 'CHROM'].astype(str) + ':' +
        df_ukbb.loc[missing_rsid, 'POS'].astype(str) + ':' +
        temp_ref.loc[missing_rsid].astype(str) + ':' +
        temp_alt.loc[missing_rsid].astype(str)
    )
    df_ukbb['ID'] = temp_id
    
    # Now add REF/ALT in correct position (after ID)
    df_ukbb['REF'] = temp_ref
    df_ukbb['ALT'] = temp_alt
    
    # Allele frequency (ImpMAF → A1FREQ)
    df_ukbb['A1FREQ'] = chunk_df['ImpMAF']
    
    # INFO: Set to constant value (deCODE doesn't provide this)
    df_ukbb['INFO'] = 1.0
    
    # Sample size
    df_ukbb['N'] = chunk_df['N']
    
    # TEST: All additive model
    df_ukbb['TEST'] = 'ADD'
    
    # Effect size and standard error
    df_ukbb['BETA'] = chunk_df['Beta']
    df_ukbb['SE'] = chunk_df['SE']
    
    # Calculate CHISQ = (BETA/SE)^2
    df_ukbb['CHISQ'] = (chunk_df['Beta'] / chunk_df['SE']) ** 2
    
    # Log10 p-value
    df_ukbb['LOG10P'] = chunk_df['minus_log10_pval']
    
    # EXTRA column (set to NA)
    df_ukbb['EXTRA'] = 'NA'
    
    # P-value
    df_ukbb['P'] = chunk_df['Pval']
    
    return df_ukbb

def transform_decode_to_ukbb(input_file, output_dir, chunksize=100000):
    """
    Transform deCODE format to UKBB format using chunked processing
    
    Parameters:
    -----------
    input_file : str
        Path to input deCODE file
    output_dir : str
        Directory for output files
    chunksize : int
        Number of rows to process at once (default 100k)
    """
    
    # Extract gene name
    gene_name = extract_gene_name(input_file)
    if gene_name is None:
        print(f"Warning: Could not extract gene name from {input_file}")
        gene_name = "UNKNOWN"
    
    print(f"Processing gene: {gene_name}")
    print(f"Input file: {input_file}")
    
    # Get file size
    file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    print(f"File size: {file_size_mb:.1f} MB")
    
    # Create output filename
    output_file = os.path.join(output_dir, f"{gene_name}_gwas_rsids.txt")
    
    # Process file in chunks
    print(f"Processing in chunks of {chunksize:,} rows...")
    first_chunk = True
    total_rows = 0
    
    try:
        for i, chunk in enumerate(pd.read_csv(input_file, sep=r'\s+', chunksize=chunksize), 1):
            # Transform chunk
            chunk_transformed = transform_chunk(chunk)
            
            # Write to file (tab-separated)
            if first_chunk:
                # Write with header
                chunk_transformed.to_csv(output_file, sep='\t', index=False, na_rep='NA', mode='w')
                first_chunk = False
            else:
                # Append without header
                chunk_transformed.to_csv(output_file, sep='\t', index=False, na_rep='NA', 
                                        mode='a', header=False)
            
            total_rows += len(chunk)
            
            # Progress update every 10 chunks
            if i % 10 == 0:
                print(f"  Processed {total_rows:,} rows ({i} chunks)...")
    
    except Exception as e:
        print(f"ERROR processing file: {e}")
        raise
    
    print(f"Complete! Processed {total_rows:,} variants for {gene_name}")
    print(f"Output written to: {output_file}")
    
    return output_file

def batch_process(input_pattern, output_dir, chunksize=100000):
    """
    Process multiple files matching a pattern
    
    Parameters:
    -----------
    input_pattern : str
        Glob pattern for input files (e.g., "*.txt")
    output_dir : str
        Directory for output files
    chunksize : int
        Number of rows to process at once
    """
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all matching files
    input_files = glob.glob(input_pattern)
    
    if not input_files:
        print(f"No files found matching pattern: {input_pattern}")
        return
    
    print(f"Found {len(input_files)} files to process")
    print(f"Output directory: {output_dir}")
    print("="*60)
    
    # Process each file
    for i, input_file in enumerate(input_files, 1):
        print(f"\n[{i}/{len(input_files)}] {input_file}")
        print("-"*60)
        try:
            transform_decode_to_ukbb(input_file, output_dir, chunksize)
        except Exception as e:
            print(f"ERROR processing {input_file}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"Batch processing complete!")
    print(f"Output files in: {output_dir}")

if __name__ == "__main__":
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Single file: python transform_decode_to_ukbb_chunked.py <input_file> <output_dir> [chunksize]")
        print("  Batch mode:  python transform_decode_to_ukbb_chunked.py <input_pattern> <output_dir> [chunksize]")
        print("\nExamples:")
        print("  python transform_decode_to_ukbb_chunked.py 13943_38_DPY30_DPY30.txt ./output/")
        print("  python transform_decode_to_ukbb_chunked.py '*_*_*_*.txt' ./output/")
        print("  python transform_decode_to_ukbb_chunked.py '*.txt' ./output/ 50000")
        print("\nNote: Default chunksize is 100,000 rows. Use smaller chunks for very tight memory limits.")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    chunksize = int(sys.argv[3]) if len(sys.argv) > 3 else 100000
    
    # Check if it's a pattern or single file
    if '*' in input_path or '?' in input_path:
        # Batch mode
        batch_process(input_path, output_dir, chunksize)
    else:
        # Single file mode
        if not os.path.exists(input_path):
            print(f"Error: File not found: {input_path}")
            sys.exit(1)
        
        os.makedirs(output_dir, exist_ok=True)
        transform_decode_to_ukbb(input_path, output_dir, chunksize)
