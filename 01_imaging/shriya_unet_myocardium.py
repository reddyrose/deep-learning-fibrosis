# Commented out IPython magic to ensure Python compatibility.
import os
import cv2
import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

plt.style.use("ggplot")
# %matplotlib inline

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

im_width = 256
im_height = 256

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
BASE_DIR = "."

image_dir = os.path.join(BASE_DIR, "ekchen/Original-images")
mask_dir = os.path.join(BASE_DIR, "ekchen/image-masks")

batch_size = 8
epochs = 100
image_size = (im_width, im_height)
n_channels = 1

model_save_file = os.path.join(BASE_DIR, "shriya/myocardium-unet-ethan.weights.h5")

"""###Data Generator"""

class DataGenerator(Sequence):
    def __init__(self, image_dir, mask_dir, split='train', batch_size=32, image_size=(256, 256), n_channels=1, shuffle=True):
        self.image_dir = image_dir
        self.mask_dir = mask_dir
        self.split = split
        self.batch_size = batch_size
        self.image_size = image_size
        self.n_channels = n_channels
        self.shuffle = shuffle
        self.image_filenames = sorted(os.listdir(image_dir))
        self.mask_filenames = sorted(os.listdir(mask_dir))
        self.on_epoch_end()

        X_train, X_test, y_train, y_test = train_test_split(self.image_filenames, self.mask_filenames, test_size=0.2, random_state=42)
        X_train, X_valid, y_train, y_valid = train_test_split(X_train, y_train, test_size=0.1, random_state=42)

        if self.split == 'train':
            self.image_filenames = X_train
            self.mask_filenames = y_train
        elif self.split == 'valid':
            self.image_filenames = X_valid
            self.mask_filenames = y_valid
        elif self.split == 'test':
            self.image_filenames = X_test
            self.mask_filenames = y_test
        self.on_epoch_end()

    def __len__(self):
        return int(np.ceil(len(self.image_filenames) / self.batch_size))

    def __getitem__(self, index):
        indexes = self.indexes[index*self.batch_size:(index+1)*self.batch_size]
        image_filenames_temp = [self.image_filenames[k] for k in indexes]
        mask_filenames_temp = [self.mask_filenames[k] for k in indexes]
        X, y = self.__data_generation(image_filenames_temp, mask_filenames_temp)
        return X, y

    def on_epoch_end(self):
        self.indexes = np.arange(len(self.image_filenames))
        if self.shuffle == True:
            np.random.shuffle(self.indexes)

    def preprocess_image(self, image):
        # Recolor image to grayscale
        recolored_image = image

        # Normalize the pixel value array to the range [0, 255]
        normalized_array = (recolored_image - np.min(recolored_image)) / (np.max(recolored_image) - np.min(recolored_image)) * 255
        normalized_array = normalized_array.astype(np.uint8)

        # Resize the image to a common size
        resized_image = resize(normalized_array, self.image_size, mode='constant', preserve_range=True)

        return resized_image

    def preprocess_mask(self, mask):
        # Normalize the mask array to the range [0, 1]
        mask[mask == 255] = 1

        # Resize the mask to a common size
        resized_mask = resize(mask, self.image_size, mode='constant', preserve_range=True)

        return resized_mask

    def __data_generation(self, image_filenames_temp, mask_filenames_temp):
        X = np.empty((self.batch_size, *self.image_size, self.n_channels))
        y = np.empty((self.batch_size, *self.image_size, 1))

        for i, (image_filename, mask_filename) in enumerate(zip(image_filenames_temp, mask_filenames_temp)):
            image = Image.open(os.path.join(self.image_dir, image_filename)).convert('L')
            mask = Image.open(os.path.join(self.mask_dir, mask_filename)).convert('L')

            image = np.array(image)
            mask = np.array(mask)

            image = self.preprocess_image(image)
            mask = self.preprocess_mask(mask)

            X[i,] = image[..., np.newaxis]
            y[i,] = mask[..., np.newaxis]  # Ensure mask has the correct shape

        return X, y

def visualize_image_and_mask(generator, index):
    # Get a batch of data
    X, y = generator[index]

    # Select the first image and mask in the batch
    image = X[0]
    mask = y[0]

    # Display the image
    plt.figure(figsize=(10, 5))

    plt.subplot(1, 2, 1)
    plt.title('Image')
    plt.imshow(image.astype(np.uint8))
    plt.axis('off')

    plt.subplot(1, 2, 2)
    plt.title('Mask')
    plt.imshow(mask.squeeze(), cmap='gray')
    plt.axis('off')

    plt.show()

training_generator = DataGenerator(image_dir, mask_dir, split='train', batch_size=batch_size, image_size=image_size, n_channels=n_channels)

# Visualize the first batch
visualize_image_and_mask(training_generator, index=0)

"""###Model"""

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

input_img = Input((im_height, im_width, 1), name='img')
model = get_unet(input_img, n_filters=16, dropout=0.05, batchnorm=True)
model.compile(optimizer=Adam(), loss="binary_crossentropy", metrics=["accuracy"])

model.summary()

callbacks = [
    EarlyStopping(patience=10, verbose=1),
    ReduceLROnPlateau(factor=0.1, patience=5, min_lr=0.00001, verbose=1),
    ModelCheckpoint(model_save_file, verbose=1, save_best_only=True, save_weights_only=True)
]

train_generator = DataGenerator(image_dir, mask_dir, split='train', batch_size=batch_size, image_size=(im_height, im_width))
valid_generator = DataGenerator(image_dir, mask_dir, split='valid', batch_size=batch_size, image_size=(im_height, im_width))

results = model.fit(train_generator,
                    epochs=100,
                    callbacks=callbacks,
                    validation_data=valid_generator,
                    validation_steps=len(valid_generator))

plt.figure(figsize=(8, 8))
plt.title("Learning curve")
plt.plot(results.history["loss"], label="loss")
plt.plot(results.history["val_loss"], label="val_loss")
plt.plot( np.argmin(results.history["val_loss"]), np.min(results.history["val_loss"]), marker="x", color="r", label="best model")
plt.xlabel("Epochs")
plt.ylabel("log_loss")
plt.legend();

"""##Model Evaluation"""

model.load_weights(model_save_file)

# Assuming you have defined a DataGenerator for testing
test_generator = DataGenerator(image_dir, mask_dir, split='test', batch_size=batch_size, image_size=(im_height, im_width))

# Evaluate the model on the testing data
evaluation = model.evaluate(test_generator, steps=len(test_generator))

# Print the evaluation results (e.g., loss and any other metrics)
print("Testing Loss:", evaluation[0])
print("Testing Metrics:", evaluation[1:])

# Set a random seed for reproducibility
random.seed(42)

# Choose a random index within the range of the generator's length
index = random.randint(0, len(test_generator) - 1)

# Get a batch of images and masks using the index
X_batch, y_batch = test_generator[index]

predictions = model.predict(X_batch)

def visualize_image_in_batch(X_batch, predictions):
    # Choose a random image index within the batch
    image_index = random.randint(0, batch_size - 1)

    # Plot the original image
    plt.figure(figsize=(10, 6))
    plt.subplot(1, 3, 1)
    plt.imshow(X_batch[image_index].squeeze(), cmap='gray')
    plt.title('Original Image')

    # Plot the ground truth mask
    plt.subplot(1, 3, 2)
    plt.imshow(y_batch[image_index].squeeze(), cmap='gray')
    plt.title('Ground Truth Mask')

    # Plot the model's predicted mask
    prediction = (predictions[image_index].squeeze() > .20).astype(np.uint8)

    plt.subplot(1, 3, 3)
    plt.imshow(prediction, cmap='gray')
    plt.title('Predicted Mask')

    plt.tight_layout()
    plt.show()

visualize_image_in_batch(X_batch, predictions)
visualize_image_in_batch(X_batch, predictions)
visualize_image_in_batch(X_batch, predictions)

def post_processing(prediction):
  processed_pred = (prediction > 0.95).astype(np.uint8)
  processed_pred = [(resize(image, (im_width, im_height, 1), mode = 'constant', preserve_range = True)) for image in processed_pred]

  #Erosion

  # Define the structuring element and apply erosion
  kernel = np.ones((3, 3), np.uint8)

  for i in range(len(processed_pred)):
    # Extract the ith binary mask
    binary_mask = processed_pred[i]

    eroded_mask = cv2.erode(binary_mask, kernel, iterations=1)

    blurred_mask = cv2.GaussianBlur(eroded_mask, (3, 3), 0)

    # Update binary_preds with the transformed mask
    processed_pred[i] = blurred_mask

  return processed_pred

def dice_coefficient(ground_truth, prediction, print_values=False):
    # Threshold the arrays to ensure they contain only 0s and 1s
    ground_truth = (ground_truth > .08).astype(np.uint8)
    prediction = (prediction > .08).astype(np.uint8)

    # Resize the arrays to ensure they contain are the same shape
    ground_truth = ground_truth.squeeze()
    prediction = prediction.squeeze()

    intersection = np.multiply(ground_truth, prediction)

    if (print_values == True):
        ("Intersection:", np.sum(intersection))
        print("Ground Truth:", np.sum(ground_truth))
        print("Prediction:", np.sum(prediction))

    dice = (2 * np.sum(intersection)) / (np.sum(ground_truth) + np.sum(prediction))
    return dice

# Initialize an empty list to store Dice scores
dice_scores = []

# Iterate over each batch in the test generator
for i in range(len(test_generator)):
    # Get a batch of images and masks
    X_batch, y_batch = test_generator[i]

    # Make predictions using the model
    predictions = model.predict(X_batch)

    # Calculate dice coefficient for each image in the batch
    for j in range(len(X_batch)):
        dice = dice_coefficient(y_batch[j], predictions[j])
        dice_scores.append(dice)

# Compute the average Dice score across all images in the test set
average_dice_score = np.mean(dice_scores)
print("Average Dice Score:", average_dice_score)

# Initialize an empty list to store Dice scores
dice_scores = []

# Iterate over each batch in the test generator
for i in range(len(valid_generator)):
    # Get a batch of images and masks
    X_batch, y_batch = test_generator[i]

    # Make predictions using the model
    predictions = model.predict(X_batch)

    # Calculate dice coefficient for each image in the batch
    for j in range(len(X_batch)):
        dice = dice_coefficient(y_batch[j], predictions[j])
        dice_scores.append(dice)

# Compute the average Dice score across all images in the test set
average_dice_score = np.mean(dice_scores)
print("Validation Set Average Dice Score:", average_dice_score)
