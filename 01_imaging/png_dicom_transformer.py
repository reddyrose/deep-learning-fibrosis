import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import pydicom
import zipfile


from PIL import Image
from tqdm import tqdm

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

zip_file_path = os.path.join(BASE_DIR, "shriya/unfiltered-test-ShMOLLI")
unzipped_temp = os.path.join(BASE_DIR, "shriya/UKBB_SHMOLLI-unzipped")
pngimages_path = os.path.join(BASE_DIR, "shriya/UKBB_SHMOLLI-pngimages")


#Unzips file in input_path and saves to extracted_path

def extract_data(input_path, extracted_path):
    if zipfile.is_zipfile(input_path): 
      with zipfile.ZipFile(input_path, "r") as zip_ref:
        zip_ref.extractall(extracted_path)


def filter_dicom(unzipped_patient_path):
    
    filtered_dicom = np.zeros((256, 256), dtype=np.uint8)
    dicom_id = ""
    
    for i in os.listdir(unzipped_patient_path):
        dicom_path = os.path.join(unzipped_patient_path, i)
        dicom = pydicom.dcmread(dicom_path, force = True)
        try:
            if ('T1MAP' in dicom[0x008,0x103E].value)&(dicom[0x020,0x0013].value ==2):
                filtered_dicom = dicom.pixel_array
                dicom_id = i[:-4]
        except:
            print(f"{dicom_path} Not a valid dicom")
        
    return filtered_dicom, dicom_id



#logic:
#loop over all zip files
#.  unzip file into a folder
#.  filter through the folder to pick the dicom we want
#.  read dicom
#   modify dicom into PNG (resized to 256 by 256)
#.  save PNG to unzip_to_path
#.  delete folder


all_zipped_files = os.listdir(zip_file_path)


for i in tqdm(all_zipped_files):
    full_path = os.path.join(zip_file_path, i)
    patient_id = i[:-4]
    
    # Save unzipped files in directory
    extract_data(full_path, unzipped_temp)

    # Get filtered dicom
    filtered_dicom, dicom_id = filter_dicom(unzipped_temp)

    # Resize filtered dicom
    resized_dicom = cv2.resize(filtered_dicom, (256, 256), interpolation=cv2.INTER_LINEAR)

    # Normalize the DICOM array to the range [0, 255]
    dicom_array = cv2.cvtColor(resized_dicom, cv2.COLOR_GRAY2RGB)
    dicom_array = (dicom_array - np.min(dicom_array)) / (np.max(dicom_array) - np.min(dicom_array)) * 255
    dicom_array = dicom_array.astype(np.uint8)

    # Convert the numpy array to PIL Image
    dicom_image = Image.fromarray(dicom_array)
    
    # Save dicom as PNG
    image_save_path = os.path.join(pngimages_path, patient_id + "_" + dicom_id + ".png")
    dicom_image.save(image_save_path, format="PNG")

    # Delete unzipped files
    for file_name in os.listdir(unzipped_temp):
       file_path = os.path.join(unzipped_temp, file_name)
       if os.path.isfile(file_path):
           os.remove(file_path)

