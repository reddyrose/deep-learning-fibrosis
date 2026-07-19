"""Optimized VAE training with efficient data loading"""

import tensorflow as tf
#import tensorflow_probability as tfp
import numpy as np
import pandas as pd
import tifffile
import cv2
import os
from tqdm import tqdm
from sklearn.model_selection import train_test_split
import time
import argparse
import matplotlib.pyplot as plt

# GPU memory growth
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image_folder", required=True,
            help="path to input image directory, requires images in tiff format")
    ap.add_argument("-o", "--output_directory", required=True,
            help="path to VAE weights file")
    ap.add_argument("-qc", "--quality_control_path", required=True,
            help="path to table with 'quality_controlled' column")
    ap.add_argument("-b", "--batch_size", required=True, type=int,
            help="batch size")
    ap.add_argument("-e", "--epochs", required=True, type=int,
            help="number of epochs to train on")
    ap.add_argument("-ld", "--latent_dim", required=True, type=int,
            help="latent dimensions of the VAE")
    return vars(ap.parse_args())

def get_bounding_box(ground_truth_map):
  # get bounding box from mask
  y_indices, x_indices = np.where(ground_truth_map > 0)
  if len(x_indices) == 0 or len(y_indices) == 0:
      return [0,0,255,255]
      
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

def preprocess_image(image):
    
  bbox = get_bounding_box(image)
  image = image[bbox[1]:bbox[3], bbox[0]:bbox[2]]
  image = cv2.resize(image, (256, 256))

  filtered_image = np.array(image)
  filtered_image = filtered_image.reshape((256, 256, 1)) 

  return filtered_image

def load_and_preprocess_image(file_path):
    """
    Load and preprocess a single image.
    To be used with tf.data.Dataset.map()
    """
    def read_and_process(file_path):
        # Read the image
        img = tifffile.imread(file_path.numpy().decode())
        img = img.astype(np.float32) / 4000.0
        processed_img = preprocess_image(img)
        
        return processed_img
    
    processed = tf.py_function(
        read_and_process,
        [file_path],
        tf.float32
    )

    processed.set_shape((256, 256, 1))

    return processed
    
def create_streaming_datasets(image_files, valid_ids, image_folder, 
                            train_val_test_split=[0.7, 0.15, 0.15],
                            batch_size=32,
                            shuffle_buffer=1000):
    # Filter valid files and get full paths
    valid_files = [os.path.join(image_folder, f) for f in image_files 
                  if f[:7] in valid_ids]
    
    # Shuffle files once before splitting
    np.random.shuffle(valid_files)
    
    # Split into train/val/test
    total_size = len(valid_files)
    train_size = int(total_size * train_val_test_split[0])
    val_size = int(total_size * train_val_test_split[1])
    
    train_files = valid_files[:train_size]
    val_files = valid_files[train_size:train_size + val_size]
    test_files = valid_files[train_size + val_size:]
    
    # Create datasets from file paths
    train_dataset = tf.data.Dataset.from_tensor_slices(train_files)
    val_dataset = tf.data.Dataset.from_tensor_slices(val_files)
    test_dataset = tf.data.Dataset.from_tensor_slices(test_files)
    
    # Set up parallel processing
    AUTOTUNE = tf.data.AUTOTUNE

    def configure_dataset(dataset, is_training=False):
        # Cache file paths (not images)
        dataset = dataset.cache()
        
        if is_training:
            dataset = dataset.shuffle(shuffle_buffer)
        
        # Load and preprocess images in parallel
        dataset = dataset.map(
            load_and_preprocess_image,
            num_parallel_calls=AUTOTUNE
        )
        
        # Batch and prefetch
        dataset = dataset.batch(batch_size)
        dataset = dataset.prefetch(AUTOTUNE)
        
        return dataset

    # Configure each dataset
    train_dataset = configure_dataset(train_dataset, is_training=True)
    val_dataset = configure_dataset(val_dataset)
    test_dataset = configure_dataset(test_dataset)
    
    return train_dataset, val_dataset, test_dataset

class CVAE(tf.keras.Model):
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
            return tf.sigmoid(logits)
        return logits

def compute_loss(model, x):
    mean, logvar = model.encode(x)
    z = model.reparameterize(mean, logvar)
    x_logit = model.decode(z)
    
    mse_loss = tf.square(x - tf.sigmoid(x_logit))
    logpx_z = -tf.reduce_sum(mse_loss, axis=[1, 2, 3])
    
    logpz = log_normal_pdf(z, 0., 0.)
    logqz_x = log_normal_pdf(z, mean, logvar)
    
    return -tf.reduce_mean(logpx_z + (logpz - logqz_x))

def log_normal_pdf(sample, mean, logvar, raxis=1):
    log2pi = tf.math.log(2. * np.pi)
    return tf.reduce_sum(
        -.5 * ((sample - mean) ** 2. * tf.exp(-logvar) + logvar + log2pi),
        axis=raxis)

@tf.function
def train_step(model, x, optimizer):
    with tf.GradientTape() as tape:
        loss = compute_loss(model, x)
    gradients = tape.gradient(loss, model.trainable_variables)
    optimizer.apply_gradients(zip(gradients, model.trainable_variables))
    return loss

def train_vae():
    args = parse_args()

    image_folder = args["image_folder"]
    output_directory = args["output_directory"]
    quality_control_path = args["quality_control_path"]
    batch_size = args["batch_size"]
    epochs = args["epochs"]
    latent_dim = args["latent_dim"]
    
    # Load quality control data
    image_files = sorted([f for f in os.listdir(image_folder) if f.endswith('.tiff')])
    
    #load OG MRI mean T1 file
    mean_T1_original = pd.read_csv(quality_control_path)
    valid_ids = mean_T1_original.loc[mean_T1_original['quality_controlled'], 'id'].astype(str).tolist()
    
    valid_image_files = [file for file in image_files if file[:7] in valid_ids]

    # Create datasets
    train_dataset, val_dataset, test_dataset = create_streaming_datasets(
        image_files=valid_image_files,
        valid_ids=valid_ids,
        image_folder=image_folder,
        batch_size=batch_size
    )
    
    # Initialize model and optimizer
    model = CVAE(args["latent_dim"])
    lr_schedule = tf.keras.optimizers.schedules.ExponentialDecay(
        initial_learning_rate=1e-3,
        decay_steps=10000,
        decay_rate=0.9,
        staircase=True)
    optimizer = tf.keras.optimizers.Adam(learning_rate=lr_schedule)

    # Training loop
    loss_history = []

    for epoch in tqdm(range(1, epochs + 1), desc="Training Epochs", unit="epoch"):
      start_time = time.time()
      for train_x in train_dataset:
        train_step(model, train_x, optimizer)
      end_time = time.time()
    
      loss = tf.keras.metrics.Mean()
      for test_x in test_dataset:
        loss(compute_loss(model, test_x))
      elbo = -loss.result()
      loss_history.append(elbo)
      print('Epoch: {}, Test set ELBO: {}, time elapse for current epoch: {}'
            .format(epoch, elbo, end_time - start_time))

    # Save model and plots
    model.build(input_shape=(256, 256, 1))
    model.save_weights(os.path.join(args["output_directory"], f"cvae_{args['latent_dim']}d_optimized.weights.h5"))
    print("Model saved at ", os.path.join(args["output_directory"], f"cvae_{args['latent_dim']}d_optimized.weights.h5"))
    
    plt.figure()
    plt.plot(loss_history)
    plt.title('Validation Loss Over Time')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.savefig(os.path.join(args["output_directory"], f"training_loss_{args['latent_dim']}d.png"))

if __name__ == "__main__":
    train_vae()
