import os
import numpy as np
import pandas as pd
import cv2
import tifffile
import matplotlib.pyplot as plt
from tqdm import tqdm

def get_bounding_box(ground_truth_map):
    # get bounding box from mask
    y_indices, x_indices = np.where(ground_truth_map > 0)
    
    # Check if there are any non-zero pixels
    if len(y_indices) == 0 or len(x_indices) == 0:
        print("Warning: No non-zero pixels found in the image")
        return [0, 0, ground_truth_map.shape[1], ground_truth_map.shape[0]]
    
    x_min, x_max = np.min(x_indices), np.max(x_indices)
    y_min, y_max = np.min(y_indices), np.max(y_indices)
    
    # add perturbation to bounding box coordinates
    H, W = ground_truth_map.shape
    x_min = max(0, x_min - 5)
    x_max = min(W, x_max + 5)
    y_min = max(0, y_min - 5)
    y_max = min(H, y_max + 5)
    bbox = [x_min, y_min, x_max, y_max]
    return bbox

def box_image(image):
    # Make sure the image is 2D for bounding box calculation
    if image.ndim > 2:
        image_2d = image.squeeze()
    else:
        image_2d = image
        
    bbox = get_bounding_box(image_2d)
    image = image[bbox[1]:bbox[3], bbox[0]:bbox[2]]
    image = cv2.resize(image, (256, 256))
    
    return image

def erode_image(image, itr=10, show_errosion=False):
    binary_mask = (image > 0).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    eroded_mask = cv2.erode(binary_mask, kernel, iterations=itr)
    
    erroded_image = image * eroded_mask
    
    if show_errosion:
        plt.figure(figsize=(12, 4))
        plt.subplot(1, 4, 1)
        plt.imshow(binary_mask, cmap='gray', vmin=0, vmax=1)
        plt.title("Original")
        plt.subplot(1, 4, 2)
        plt.imshow(eroded_mask, cmap='gray', vmin=0, vmax=1)
        plt.title("Eroded Mask")
        plt.subplot(1, 4, 3)
        plt.imshow(binary_mask - eroded_mask, cmap='gray', vmin=0, vmax=1)
        plt.title("Difference")
        
        plt.subplot(1, 4, 4)
        plt.imshow(erroded_image, cmap='gray')
        plt.title("Eroded Image")
        plt.tight_layout()
        plt.show()
    
    return erroded_image

def calculate_statistics(image):
    # Get non-zero pixel values
    non_zero_pixels = image[image > 0]
    
    # Check if there are any non-zero pixels
    if len(non_zero_pixels) == 0:
        return {
            'mean': np.nan,
            'std': np.nan,
            'p0.25': np.nan,
            'p1': np.nan,
            'p25': np.nan,
            'p50': np.nan,
            'p75': np.nan,
            'p99': np.nan,
            'p99.5': np.nan
        }
    
    # Calculate statistics
    stats = {
        'mean': np.mean(non_zero_pixels),
        'std': np.std(non_zero_pixels),
        'p0.25': np.percentile(non_zero_pixels, 0.25),
        'p1': np.percentile(non_zero_pixels, 1),
        'p25': np.percentile(non_zero_pixels, 25),
        'p50': np.percentile(non_zero_pixels, 50),
        'p75': np.percentile(non_zero_pixels, 75),
        'p99': np.percentile(non_zero_pixels, 99),
        'p99.5': np.percentile(non_zero_pixels, 99.5)
    }
    
    return stats

# This script hardcodes an erosion depth of 8 iterations (see erode_image()
# call and the "_8itr_erroded" paths below). The pipeline also references
# 2/4/6/10-iteration sibling outputs (e.g. T1_percentiles_PheWAS_2itr_erroded,
# ...4itr..., ...6itr..., ...10itr... consumed by 04_pwas/Protien_GWAS_prep.ipynb,
# and a 10itr variant consumed downstream in 06_mr/), produced by re-running
# this script with itr and the output paths below edited by hand for each
# depth. To regenerate a different iteration depth, change itr=8 in
# erode_image() and the "8itr_erroded"/"8itr" strings below accordingly.
def main():
    # BASE_DIR should point to the root data directory on your system
    # (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
    BASE_DIR = "."

    # Set directory path
    directory = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update/SAM_masks")
    output_directory = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update/SAM_masks_8itr_erroded")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        print(f"Created output directory: {output_directory}")
    
    # Get list of TIFF files
    tiff_files = [f for f in os.listdir(directory) if f.endswith('.tif') or f.endswith('.tiff')]
    
    # Create empty list to store results
    results = []
    
    # Process each TIFF file
    print(f"Processing {len(tiff_files)} TIFF files...")
    for tiff_file in tqdm(tiff_files):
        try:
            # Extract patient ID (first 7 characters of the filename)
            patient_id = tiff_file[:7]
            
            # Load the TIFF image
            tiff_path = os.path.join(directory, tiff_file)
            image = tifffile.imread(tiff_path)
            
            # Process the image
            image = box_image(image)
            eroded_image = erode_image(image, itr=8, show_errosion=False)
            
            # Save the eroded image
            output_path = os.path.join(output_directory, tiff_file)
            tifffile.imwrite(output_path, eroded_image)
            
            # Calculate statistics
            stats = calculate_statistics(eroded_image)
            
            # Add patient ID to statistics
            stats['patient_id'] = patient_id
            
            # Add to results
            results.append(stats)
            
        except Exception as e:
            print(f"Error processing {tiff_file}: {e}")
    
    # Convert results to DataFrame
    df = pd.DataFrame(results)
    
    # Reorder columns to have patient_id first
    columns = ['patient_id', 'mean', 'std', 'p0.25', 'p1', 'p25', 'p50', 'p75', 'p99', 'p99.5']
    df = df[columns]
    
    # Save to CSV
    output_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update/T1_percentiles_8itr_erroded.csv")
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()
