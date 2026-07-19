# -*- coding: utf-8 -*-
"""deploy_unet_segmenetaion.ipynb

"""#Set up environment"""

from IPython import display

import glob
import imageio
import matplotlib.pyplot as plt
import numpy as np
import PIL
import tensorflow as tf
import tensorflow_probability as tfp
import time
import pandas as pd
from tqdm import tqdm
import tifffile

import os
import numpy as np
from PIL import Image
from sklearn.model_selection import train_test_split
import tensorflow as tf

from pickle import FALSE

import argparse

"""## Load arguements """

"""#ARGUMENTS NEEDED:

    model_weights: '<BASE_DIR>/Heart_MRI_model_weights/myocardium-unet-256.h5'
    image_path: "<BASE_DIR>/Heart_MRI/filtered-test-ShMOLLI-pngimages/"
    output_path: "<BASE_DIR>/Heart_MRI/filtered-test-ShMOLLI-pngimages/"
    dimensions: 6

    """
ap = argparse.ArgumentParser()

ap.add_argument("-mw", "--model_weights", required=True,
        help="path to .h file of VAE weights")
ap.add_argument("-i", "--image_path", required=True,
        help="path to input image directory, requires images in png format")
ap.add_argument("-o", "--output_path", required=True,
        help="path to output directory, will save a statistics.txt, mean_T1.csv, and mask_array directory")
ap.add_argument("-d", "--latent_dimensions", required=True, type=int,
        help="number of dimensions corresponding to the model who weights are intialized")


args = vars(ap.parse_args())

model_weights = args["model_weights"]
image_path = args["image_path"]
output_path = args["output_path"]
latent_dim = args["latent_dimensions"]

"""##Load the Model"""
#Define the Model and Load Weights

class CVAE(tf.keras.Model):
    """Convoutional Variational Autoencoder with input shape (256, 256, 1)."""

    def __init__(self, latent_dim):
        super(CVAE, self).__init__()   

        self.latent_dim = latent_dim
        self.encoder = tf.keras.Sequential([
            tf.keras.layers.InputLayer(input_shape=(256, 256, 1)),
            tf.keras.layers.Conv2D(32, 3, strides=2, activation='relu'),
            tf.keras.layers.Conv2D(64, 3, strides=2, activation='relu'),
            tf.keras.layers.Conv2D(128, 3, strides=2, activation='relu'),
            tf.keras.layers.Conv2D(256, 3, strides=2, activation='relu'),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(latent_dim + latent_dim),
        ])

        self.decoder = tf.keras.Sequential([
            tf.keras.layers.InputLayer(input_shape=(latent_dim,)),
            tf.keras.layers.Dense(16 * 16 * 256, activation='relu'),
            tf.keras.layers.Reshape((16, 16, 256)),
            tf.keras.layers.Conv2DTranspose(256, 4, strides=2, padding='same', activation='relu'),
            tf.keras.layers.Conv2DTranspose(128, 4, strides=2, padding='same', activation='relu'),
            tf.keras.layers.Conv2DTranspose(64, 4, strides=2, padding='same', activation='relu'),
            tf.keras.layers.Conv2DTranspose(1, 4, strides=2, padding='same'),
        ])

    @tf.function
    def sample(self, eps=None):
        if eps is None:
            eps = tf.random.normal(shape=(100, self.latent_dim))
        return self.decode(eps, apply_sigmoid=True)

    def encode(self, x):
        mean, logvar = tf.split(self.encoder(x), num_or_size_splits=2, axis=1)
        return mean, logvar

    def reparameterize(self, mean, logvar):
        eps = tf.random.normal(shape=mean.shape)
        return eps * tf.exp(logvar * .5) + mean

    def decode(self, z, apply_sigmoid=False):
        logits = self.decoder(z)
        if apply_sigmoid:
            probs = tf.sigmoid(logits)
            return probs
        return logits

    def call(self, inputs):
        mean, logvar = self.encode(inputs)
        z = self.reparameterize(mean, logvar)
        return self.decode(z)

model = CVAE(latent_dim)

# Build the model using input shapes
model.build(input_shape=(256, 256, 1))

model.load_weights(model_weights)

# Preprocess the input image (load in grayscale and normalize)
def preprocess_image(image_path):
    # Load image in grayscale, resize, and normalize
    img = tifffile.imread(image_path)  # 'L' mode converts to grayscale
    img_array = np.array(img, dtype=np.float32) / 4000.0  # Normalize to [0,1]
    
    # Add a batch dimension (for compatibility with the model)
    img_array = np.expand_dims(img_array, axis=-1)  # Add channel dimension (1 for grayscale)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    return img_array

def post_processing(prediction, threshold):
    processed = np.where(prediction < threshold, 0, prediction)
    return processed

def get_mean_T1(image):
  image = np.array(image)
  image = image * 4000

  ROI_T1_values = image[image != 0]

  mean_T1_value = np.mean(ROI_T1_values)

  return image, mean_T1_value

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

def process_dicom_files(image_dir, output_dir):
    
    #Ensure the VAE-masks directory exists
    mask_output_dir = os.path.join(output_dir, "VAE_masks")
    os.makedirs(mask_output_dir, exist_ok=True)
    
    # Define the output CSV file path
    output_csv_path = os.path.join(output_dir, "percentiles_T1_latent_spaces.csv")

    # Create the CSV file with headers if it doesn't exist
    if not os.path.exists(output_csv_path):
        df = pd.DataFrame(columns=[
            'Patient_ID', 'Mean_T1', 'T1_Standard_Deviation', 'T1_0.25th_Percentile',
            'T1_1th_Percentile', 'T1_25th_Percentile', 'T1_50th_Percentile',
            'T1_75th_Percentile', 'T1_99th_Percentile', 'T1_99.75th_Percentile',
            'Latent_0', 'Latent_1', 'Latent_2', 'Latent_3', 'Latent_4', 'Latent_5', 'Latent_6', 'Latent_7',
            'Latent_8', 'Latent_9', 'Latent_10', 'Latent_11', 'Latent_12', 'Latent_13', 'Latent_14', 'Latent_15'
        ])
        df.to_csv(output_csv_path, index=False)

    for filename in tqdm(os.listdir(image_dir)):
        if filename.endswith(".tiff"):
            #Save patient ID
            patient_ID = os.path.splitext(os.path.basename(filename))[0]

            #Transform into Image type and preproccess
            image = preprocess_image((os.path.join(image_dir, filename)))
            
            #Get predicted mask
            mean, logvar = model.encode(image)
            z = model.reparameterize(mean, logvar)

            latent_space = mean.numpy().flatten()

            prediction = model.sample(z)

            #Post-processing
            prediction = post_processing(prediction, 0.18)

            #Get mean_TI
            mean_T1_ROI, mean_T1 = get_mean_T1(prediction)

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
                'Latent_0': latent_space[0],
                'Latent_1': latent_space[1], 
                'Latent_2': latent_space[2], 
                'Latent_3': latent_space[3],
                'Latent_4': latent_space[4],
                'Latent_5': latent_space[5],
                'Latent_6': latent_space[6],
                'Latent_7': latent_space[7],
                'Latent_8': latent_space[8],
                'Latent_9': latent_space[9],
                'Latent_10': latent_space[10],
                'Latent_11': latent_space[11],
                'Latent_12': latent_space[12],
                'Latent_13': latent_space[13],
                'Latent_14': latent_space[14],
                'Latent_15': latent_space[15]
            }
            
            # Append the current row to the CSV file
            row_df = pd.DataFrame([row_data])
            row_df.to_csv(output_csv_path, mode='a', header=False, index=False)

            # Output mask with patient ID as filename
            raw_prediction_image = Image.fromarray((tf.squeeze(prediction).numpy() * 255).astype('uint8'))
            raw_prediction_image.save(os.path.join(mask_output_dir, f"{patient_ID}_VAE_prediction.tiff"))


# Implement
process_dicom_files(image_path, output_path)
