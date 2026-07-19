import pandas as pd
import numpy as np
import cv2
from PIL import Image
import os

def check_donut(image_path):
    # Load the image (replace 'image_path' with your actual image path)
    image = np.array(Image.open(image_path))
    image = image[..., np.newaxis]  # Ensure the image has a channel dimension if needed

    # Apply binary thresholding to get a binary image
    binary_image = (image > 0).astype(np.uint8)

    # Find contours in the binary image
    contours, _ = cv2.findContours(binary_image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    # Count the number of closed loops (circles)
    circle_count = 0

    # Loop through contours to check for closed loops
    for contour in contours:
        if cv2.arcLength(contour, True) > 0:
            circle_count += 1

    # Check if there are exactly two circles
    contains_two_circles = circle_count == 2

    return contains_two_circles

def update_csv_files(myocardium_csv_path, septum_csv_path, mask_files_dir):
    # Load the CSV files
    unet_myocardium_data = pd.read_csv(myocardium_csv_path)
    unet_septum_data = pd.read_csv(septum_csv_path)

    # Initialize the 'quality_controlled' column with False
    unet_myocardium_data['quality_controlled'] = False
    unet_septum_data['quality_controlled'] = False

    # List all mask files
    mask_files = [os.path.join(mask_files_dir, file) for file in os.listdir(mask_files_dir) if file.endswith('.tiff')]

    print(mask_files)

    # Create a mapping from patient_id to mask file path
    mask_file_mapping = {}
    for mask_file in mask_files:
        for patient_id in unet_myocardium_data['Patient_ID']:
            if patient_id in mask_file:
                mask_file_mapping[patient_id] = mask_file


    print(mask_file_mapping)

    # Update 'quality_controlled' column in unet_myocardium_data
    for index, row in unet_myocardium_data.iterrows():
        patient_id = row['Patient_ID']
        if patient_id in mask_file_mapping:
            mask_path = mask_file_mapping[patient_id]
            is_donut = check_donut(mask_path)
            print(is_donut)
            unet_myocardium_data.at[index, 'quality_controlled'] = is_donut

    # Update 'quality_controlled' column in unet_septum_data
    for index, row in unet_septum_data.iterrows():
        patient_id = row['Patient_ID']
        if patient_id in mask_file_mapping:
            mask_path = mask_file_mapping[patient_id]
            is_donut = check_donut(mask_path)
            unet_septum_data.at[index, 'quality_controlled'] = is_donut

    # Save the updated CSV files
    unet_myocardium_data.to_csv(myocardium_csv_path, index=False)
    unet_septum_data.to_csv(septum_csv_path, index=False)

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

# Paths to the CSV files and the directory containing mask files
myocardium_csv_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/mean_T1.csv")
septum_csv_path = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-septum/mean_T1.csv")
mask_files_dir = os.path.join(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium/SAM_masks")

# Update CSV files
update_csv_files(myocardium_csv_path, septum_csv_path, mask_files_dir)