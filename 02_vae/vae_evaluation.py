"""VAE Model Evaluation Script"""

import tensorflow as tf
import numpy as np
import pandas as pd
import tifffile
import cv2
import os
from tqdm import tqdm
import argparse
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

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
            help="path to save evaluation results")
    ap.add_argument("-qc", "--quality_control_path", required=True,
            help="path to table with 'quality_controlled' column")
    ap.add_argument("-m", "--model_path", required=True,
            help="path to trained VAE weights file")
    ap.add_argument("-b", "--batch_size", type=int, default=32,
            help="batch size")
    ap.add_argument("-ld", "--latent_dim", required=True, type=int,
            help="latent dimensions of the VAE")
    ap.add_argument("-n", "--num_samples", type=int, default=10,
            help="number of sample images to visualize")
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
    
def create_test_dataset(image_files, valid_ids, image_folder, batch_size=32):
    # Filter valid files and get full paths
    valid_files = [os.path.join(image_folder, f) for f in image_files 
                  if f[:7] in valid_ids]
    
    # Create dataset from file paths
    test_dataset = tf.data.Dataset.from_tensor_slices(valid_files)
    
    # Set up parallel processing
    AUTOTUNE = tf.data.AUTOTUNE

    # Configure dataset
    test_dataset = test_dataset.cache()
    test_dataset = test_dataset.map(
        load_and_preprocess_image,
        num_parallel_calls=AUTOTUNE
    )
    test_dataset = test_dataset.batch(batch_size)
    test_dataset = test_dataset.prefetch(AUTOTUNE)
    
    return test_dataset

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

    def call(self, x):
        mean, logvar = self.encode(x)
        z = self.reparameterize(mean, logvar)
        reconstructed = self.decode(z, apply_sigmoid=True)
        return reconstructed

def dice_coefficient(y_true, y_pred, smooth=1e-6):
    """Calculate Dice coefficient between two binary images"""
    # Binarize the images
    y_true_bin = (y_true > 0.5).astype(np.float32)
    y_pred_bin = (y_pred > 0.5).astype(np.float32)
    
    intersection = np.sum(y_true_bin * y_pred_bin)
    return (2. * intersection + smooth) / (np.sum(y_true_bin) + np.sum(y_pred_bin) + smooth)

def calculate_metrics(original, reconstruction):
    """Calculate all required metrics between original and reconstruction"""
    # MSE
    mse = np.mean((original - reconstruction) ** 2)
    
    # PSNR (using skimage)
    psnr_value = psnr(original.squeeze(), reconstruction.squeeze(), data_range=1.0)
    
    # SSIM (using skimage)
    ssim_value = ssim(original.squeeze(), reconstruction.squeeze(), data_range=1.0)
    
    # Dice coefficient
    dice = dice_coefficient(original, reconstruction)
    
    return {
        'mse': mse,
        'psnr': psnr_value,
        'ssim': ssim_value,
        'dice': dice
    }

def visualize_results(originals, reconstructions, indices, output_path, metrics=None):
    """
    Create side-by-side visualizations for selected image indices
    """
    n = len(indices)
    fig, axes = plt.subplots(n, 2, figsize=(10, n*5))
    
    for i, idx in enumerate(indices):
        # Handle the case of only one sample
        if n == 1:
            ax1, ax2 = axes[0], axes[1]
        else:
            ax1, ax2 = axes[i, 0], axes[i, 1]
            
        # Original
        ax1.imshow(originals[idx].squeeze(), cmap='gray')
        ax1.set_title('Original')
        ax1.axis('off')
        
        # Reconstruction
        ax2.imshow(reconstructions[idx].squeeze(), cmap='gray')
        ax2.set_title('Reconstruction')
        ax2.axis('off')
        
        # Add metrics if provided
        if metrics:
            if n == 1:
                plt.figtext(0.5, 0.01, 
                        f"MSE: {metrics[idx]['mse']:.4f}, PSNR: {metrics[idx]['psnr']:.2f} dB, "
                        f"SSIM: {metrics[idx]['ssim']:.4f}, Dice: {metrics[idx]['dice']:.4f}",
                        ha="center", fontsize=10, bbox={"facecolor":"white", "alpha":0.5})
            else:
                plt.figtext(0.5, 0.01 + i*(1.0/n), 
                        f"MSE: {metrics[idx]['mse']:.4f}, PSNR: {metrics[idx]['psnr']:.2f} dB, "
                        f"SSIM: {metrics[idx]['ssim']:.4f}, Dice: {metrics[idx]['dice']:.4f}",
                        ha="center", fontsize=10, bbox={"facecolor":"white", "alpha":0.5})
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, "reconstructions.png"), dpi=300)
    plt.close()

def plot_pixel_distributions(originals, reconstructions, output_path):
    """Plot histograms of pixel values for originals and reconstructions"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # Flatten all images into 1D arrays
    orig_pixels = originals.reshape(-1)
    recon_pixels = reconstructions.reshape(-1)
    
    # Plot histograms
    axes[0].hist(orig_pixels, bins=50, alpha=0.7, color='blue')
    axes[0].set_title('Original Image Pixel Distribution')
    axes[0].set_xlabel('Pixel Value')
    axes[0].set_ylabel('Frequency')
    
    axes[1].hist(recon_pixels, bins=50, alpha=0.7, color='orange')
    axes[1].set_title('Reconstructed Image Pixel Distribution')
    axes[1].set_xlabel('Pixel Value')
    axes[1].set_ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, "pixel_distributions.png"), dpi=300)
    plt.close()
    
    # Also create a combined histogram
    plt.figure(figsize=(10, 6))
    plt.hist(orig_pixels, bins=50, alpha=0.5, color='blue', label='Original')
    plt.hist(recon_pixels, bins=50, alpha=0.5, color='orange', label='Reconstruction')
    plt.title('Pixel Value Distribution Comparison')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    plt.legend()
    plt.savefig(os.path.join(output_path, "combined_pixel_distribution.png"), dpi=300)
    plt.close()

def evaluate_vae():
    args = parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args["output_directory"], exist_ok=True)
    
    image_folder = args["image_folder"]
    output_directory = args["output_directory"]
    quality_control_path = args["quality_control_path"]
    model_path = args["model_path"]
    batch_size = args["batch_size"]
    latent_dim = args["latent_dim"]
    num_samples = args["num_samples"]
    
    # Load quality control data
    image_files = sorted([f for f in os.listdir(image_folder) if f.endswith('.tiff')])
    
    # Load quality control data
    mean_T1_original = pd.read_csv(quality_control_path)
    valid_ids = mean_T1_original.loc[mean_T1_original['quality_controlled'], 'id'].astype(str).tolist()
    
    valid_image_files = [file for file in image_files if file[:7] in valid_ids]

    # Create test dataset
    test_dataset = create_test_dataset(
        image_files=valid_image_files,
        valid_ids=valid_ids,
        image_folder=image_folder,
        batch_size=batch_size
    )
    
    # Initialize model
    model = CVAE(latent_dim)
    # Build model with dummy input to initialize weights
    dummy_input = tf.zeros((1, 256, 256, 1))
    _ = model(dummy_input)
    
    # Load weights
    model.load_weights(model_path)
    print(f"Loaded model weights from {model_path}")
    
    # Evaluate model on test dataset
    print("Evaluating model...")
    
    # Lists to store results
    all_originals = []
    all_reconstructions = []
    all_metrics = []
    
    for batch in tqdm(test_dataset, desc="Processing batches"):
        # Get reconstructions
        reconstructions = model(batch)
        
        # Convert to numpy for metric calculation
        originals_np = batch.numpy()
        reconstructions_np = reconstructions.numpy()
        
        # Store images
        all_originals.append(originals_np)
        all_reconstructions.append(reconstructions_np)
        
        # Calculate metrics for each image in batch
        for i in range(originals_np.shape[0]):
            metrics = calculate_metrics(originals_np[i], reconstructions_np[i])
            all_metrics.append(metrics)
    
    # Concatenate all batches
    all_originals = np.concatenate(all_originals, axis=0)
    all_reconstructions = np.concatenate(all_reconstructions, axis=0)
    
    # Calculate average metrics
    avg_metrics = {
        'mse': np.mean([m['mse'] for m in all_metrics]),
        'psnr': np.mean([m['psnr'] for m in all_metrics]),
        'ssim': np.mean([m['ssim'] for m in all_metrics]),
        'dice': np.mean([m['dice'] for m in all_metrics])
    }
    
    # Display and save average metrics
    print("\nAverage Metrics:")
    print(f"MSE: {avg_metrics['mse']:.4f}")
    print(f"PSNR: {avg_metrics['psnr']:.2f} dB")
    print(f"SSIM: {avg_metrics['ssim']:.4f}")
    print(f"Dice Score: {avg_metrics['dice']:.4f}")
    
    # Save metrics to CSV
    metrics_df = pd.DataFrame(all_metrics)
    metrics_df.to_csv(os.path.join(output_directory, "metrics.csv"), index=False)
    
    # Save summary metrics
    with open(os.path.join(output_directory, "summary_metrics.txt"), 'w') as f:
        f.write(f"MSE: {avg_metrics['mse']:.4f}\n")
        f.write(f"PSNR: {avg_metrics['psnr']:.2f} dB\n")
        f.write(f"SSIM: {avg_metrics['ssim']:.4f}\n")
        f.write(f"Dice Score: {avg_metrics['dice']:.4f}\n")
    
    # Visualize sample images
    print("\nGenerating visualizations...")
    sample_indices = np.random.choice(len(all_originals), min(num_samples, len(all_originals)), replace=False)
    visualize_results(all_originals, all_reconstructions, sample_indices, output_directory, all_metrics)
    
    # Plot pixel distributions
    plot_pixel_distributions(all_originals, all_reconstructions, output_directory)
    
    print(f"\nEvaluation complete. Results saved to {output_directory}")

if __name__ == "__main__":
    evaluate_vae()
