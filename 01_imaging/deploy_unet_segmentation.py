# -*- coding: utf-8 -*-
"""deploy_unet_segmenetaion.ipynb

"""#Set up environment"""

import os
import cv2
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from PIL import Image
import tifffile

from tqdm import tqdm_notebook, tnrange
from itertools import chain
from skimage.io import imread, imshow, concatenate_images
from skimage.transform import resize
from skimage.morphology import label
from sklearn.model_selection import train_test_split

import tensorflow as tf

from keras.models import Model, load_model
from keras.layers import Input, BatchNormalization, Activation, Dense, Dropout
from keras.layers import Lambda, RepeatVector, Reshape
from keras.layers import Conv2D, Conv2DTranspose
from keras.layers import MaxPooling2D, GlobalMaxPool2D
from keras.layers import concatenate, add
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
from tensorflow.keras.utils import Sequence

import argparse

"""## Load arguements """

"""#ARGUMENTS NEEDED:

    unet_weights: '<BASE_DIR>/Heart_MRI_model_weights/myocardium-unet-256.h5'
    image_path: "<BASE_DIR>/Heart_MRI/filtered-test-ShMOLLI-pngimages/"
    output_path: "<BASE_DIR>/Heart_MRI/filtered-test-ShMOLLI-pngimages/"
    threshold: 0.08

    """
ap = argparse.ArgumentParser()

ap.add_argument("-t", "--threshold", required=True,
        help="threshold of segmentation, used in post processing")
ap.add_argument("-uw", "--unet_weights", required=True,
        help="path to .h file of unet weights")
ap.add_argument("-i", "--image_path", required=True,
        help="path to input image directory, requires images in png format")
ap.add_argument("-o", "--output_path", required=True,
        help="path to output directory, will save a statistics.txt, mean_T1.csv, and mask_array directory")


args = vars(ap.parse_args())

threshold = float(args["threshold"])
unet_weights = args["unet_weights"]
image_path = args["image_path"]
output_path = args["output_path"]


"""##Load the Unet"""

#Define a UNet and apply the pretrained weights

def conv2d_block(input_tensor, n_filters, kernel_size = 3, batchnorm = True):
    """Function to add 2 convolutional layers with the parameters passed to it"""
    # first layer
    x = Conv2D(filters = n_filters, kernel_size = (kernel_size, kernel_size),\
              kernel_initializer = 'he_normal', padding = 'same')(input_tensor)
    if batchnorm:
        x = BatchNormalization()(x)
    x = Activation('relu')(x)

    # second layer
    x = Conv2D(filters = n_filters, kernel_size = (kernel_size, kernel_size),\
              kernel_initializer = 'he_normal', padding = 'same')(input_tensor)
    if batchnorm:
        x = BatchNormalization()(x)
    x = Activation('relu')(x)

    return x

def get_unet(input_img, n_filters = 16, dropout = 0.1, batchnorm = True):
    """Function to define the UNET Model"""
    # Contracting Path
    c1 = conv2d_block(input_img, n_filters * 1, kernel_size = 3, batchnorm = batchnorm)
    p1 = MaxPooling2D((2, 2))(c1)
    p1 = Dropout(dropout)(p1)

    c2 = conv2d_block(p1, n_filters * 2, kernel_size = 3, batchnorm = batchnorm)
    p2 = MaxPooling2D((2, 2))(c2)
    p2 = Dropout(dropout)(p2)

    c3 = conv2d_block(p2, n_filters * 4, kernel_size = 3, batchnorm = batchnorm)
    p3 = MaxPooling2D((2, 2))(c3)
    p3 = Dropout(dropout)(p3)

    c4 = conv2d_block(p3, n_filters * 8, kernel_size = 3, batchnorm = batchnorm)
    p4 = MaxPooling2D((2, 2))(c4)
    p4 = Dropout(dropout)(p4)

    c5 = conv2d_block(p4, n_filters = n_filters * 16, kernel_size = 3, batchnorm = batchnorm)

    # Expansive Path
    u6 = Conv2DTranspose(n_filters * 8, (3, 3), strides = (2, 2), padding = 'same')(c5)
    u6 = concatenate([u6, c4])
    u6 = Dropout(dropout)(u6)
    c6 = conv2d_block(u6, n_filters * 8, kernel_size = 3, batchnorm = batchnorm)

    u7 = Conv2DTranspose(n_filters * 4, (3, 3), strides = (2, 2), padding = 'same')(c6)
    u7 = concatenate([u7, c3])
    u7 = Dropout(dropout)(u7)
    c7 = conv2d_block(u7, n_filters * 4, kernel_size = 3, batchnorm = batchnorm)

    u8 = Conv2DTranspose(n_filters * 2, (3, 3), strides = (2, 2), padding = 'same')(c7)
    u8 = concatenate([u8, c2])
    u8 = Dropout(dropout)(u8)
    c8 = conv2d_block(u8, n_filters * 2, kernel_size = 3, batchnorm = batchnorm)

    u9 = Conv2DTranspose(n_filters * 1, (3, 3), strides = (2, 2), padding = 'same')(c8)
    u9 = concatenate([u9, c1])
    u9 = Dropout(dropout)(u9)
    c9 = conv2d_block(u9, n_filters * 1, kernel_size = 3, batchnorm = batchnorm)

    outputs = Conv2D(1, (1, 1), activation='sigmoid')(c9)
    model = Model(inputs=[input_img], outputs=[outputs])

    return model

input_img = Input((256, 256, 1), name='img')
unet_model = get_unet(input_img, n_filters=16, dropout=0.05, batchnorm=True)

unet_model.load_weights(unet_weights)

def predict(image, threshold):

  prediction = unet_model.predict(image)

  print(np.min(prediction))

  prediction = np.array(prediction[0])
  prediction = (prediction > threshold).astype(np.uint8)

  return prediction

def get_mean_T1(image, ROI):
  image = np.array(image)
  ROI = np.array(ROI)

  mean_T1_ROI = ROI * image
  mean_T1_ROI = mean_T1_ROI * (4000/255)

  # Calculate mean T1 value
  sum_ROI = np.sum(ROI)
  if sum_ROI == 0:
    mean_T1_value = 0
  else:
    mean_T1_value = np.sum(mean_T1_ROI) / sum_ROI  # Mean within ROI
  
  return mean_T1_ROI, mean_T1_value

def calculate_statistics(values):
  ROI_T1_values = values[values != 0]

  if ROI_T1_values.size == 0:
    return 0, 0, 0, 0, 0, 0, 0, 0    

  std_dev_t1 = np.std(ROI_T1_values)
  percentile_99 = np.percentile(ROI_T1_values, 99)
  percentile_75 = np.percentile(ROI_T1_values, 75)
  percentile_50 = np.percentile(ROI_T1_values, 50)  # Median
    
  percentile_0_25 = np.percentile(ROI_T1_values, 0.25)
  percentile_1 = np.percentile(ROI_T1_values, 1)
  percentile_25 = np.percentile(ROI_T1_values, 25)  
  percentile_99_75 = np.percentile(ROI_T1_values, 99.75)  
    
  return std_dev_t1, percentile_99, percentile_75, percentile_50, percentile_0_25, percentile_1, percentile_25, percentile_99_75

""" Complete Workflow """

def preprocess_image(image):
    # Recolor image to grayscale
    recolored_image = image

    # Normalize the pixel value array to the range [0, 255]
    normalized_array = (recolored_image - np.min(recolored_image)) / (np.max(recolored_image) - np.min(recolored_image)) * 255
    normalized_array = normalized_array.astype(np.uint8)

    # Resize the image to a common size
    resized_image = resize(normalized_array, (256,256), mode='constant', preserve_range=True)

    return resized_image

def postprocess_prediction(prediction):
    contours, _ = cv2.findContours(prediction, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Check if there are any contours found
    if not contours:
        return prediction

    # Find the largest contour based on area
    largest_contour = max(contours, key=cv2.contourArea)

    # Create a mask of the largest contour
    mask = np.zeros_like(prediction)
    cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # Apply the mask to the original image to keep only the largest contour
    result = cv2.bitwise_and(prediction, mask)
    result = result[..., np.newaxis]

    return result

def process_dicom_files(image_dir, output_dir, threshold):
    
    #Ensure the SAM-masks directory exists
    mask_output_dir = os.path.join(output_dir, "SAM_masks")
    os.makedirs(mask_output_dir, exist_ok=True)
    
    # Define the output CSV file path
    output_csv_path = os.path.join(output_dir, "percentiles_T1.csv")
    processed_files_path = os.path.join(output_dir, "processed_files.txt")

    # Create the CSV file with headers if it doesn't exist
    if not os.path.exists(output_csv_path):
        df = pd.DataFrame(columns=['Patient_ID', 'Mean_T1', 'T1_Standard_Deviation', 'T1_0.25th_Percentile', 'T1_1th_Percentile',  'T1_25th_Percentile', 'T1_50th_Percentile', 'T1_75th_Percentile', 'T1_99th_Percentile', 'T1_99.75th_Percentile'])
        df.to_csv(output_csv_path, index=False)

    # Create the processed_files.txt if it doesn't exist
    if not os.path.exists(processed_files_path):
        with open(processed_files_path, 'w') as file:
            pass  # Just to create the file


    # Read the list of processed files
    if os.path.exists(processed_files_path):
        with open(processed_files_path, 'r') as file:
            processed_files = set(file.read().splitlines())
    else:
        processed_files = set()


    for filename in tqdm(os.listdir(image_dir)):
        
        if filename.endswith(".png") and filename not in processed_files:
            #Save patient ID
            patient_ID = os.path.splitext(os.path.basename(filename))[0]

            #Transform into Image type
            data = Image.open(os.path.join(image_dir, filename)).convert('L')
            image = preprocess_image(np.array(data))
            image = image[..., np.newaxis]
            image = np.expand_dims(image, axis=0)

            #Get predicted mask
            prediction = predict(image, threshold)
            print(prediction.shape)

            prediction = postprocess_prediction(prediction)

            print(prediction.shape)

            #Get mean_TI
            mean_T1_ROI, mean_T1 = get_mean_T1(image[0], prediction)

            # Calculate statistics
            std_dev_t1, percentile_99, percentile_75, percentile_50, percentile_0_25, percentile_1, percentile_25, percentile_99_75 = calculate_statistics(mean_T1_ROI)
               
            row_data = {
                'Patient_ID': patient_ID,
                'Mean_T1': mean_T1,
                'T1_Standard_Deviation': std_dev_t1,
                'T1_0.25th_Percentile': percentile_0_25,
                'T1_1th_Percentile': percentile_1,
                'T1_25th_Percentile': percentile_25,
                'T1_50th_Percentile': percentile_50,
                'T1_75th_Percentile': percentile_75,
                'T1_99th_Percentile': percentile_99,
                'T1_99.75th_Percentile': percentile_99_75,

            }
            
            # Append the current row to the CSV file
            row_df = pd.DataFrame([row_data])
            row_df.to_csv(output_csv_path, mode='a', header=False, index=False)

            # Output mask with patient ID as filename
            tifffile.imwrite(os.path.join(mask_output_dir, f"{patient_ID}_mask.tiff"), mean_T1_ROI.astype(np.float32))

            # Append the filename to the processed files list
            #with open(processed_files_path, 'a') as file:
            #    file.write(filename + '\n')

  
    
# Implement
process_dicom_files(image_path, output_path, threshold)
