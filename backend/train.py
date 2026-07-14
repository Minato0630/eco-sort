import os
import json
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Configurations
DATASET_DIR = "dataset"
MODEL_PATH = "backend/waste_classifier.h5"
CLASSES_PATH = "backend/class_indices.json"
EPOCHS = 8
BATCH_SIZE = 4
IMAGE_SIZE = (224, 224)

def setup_directories():
    # If dataset/ doesn't exist, create mock training folders
    classes = ["Organic", "Plastic", "Paper", "Metal", "E-Waste", "General"]
    os.makedirs(DATASET_DIR, exist_ok=True)
    for c in classes:
        os.makedirs(os.path.join(DATASET_DIR, c), exist_ok=True)
    print(f"Dataset folders created under '{DATASET_DIR}/'.")
    print("Please populate these folders with training images and run this script again!")

def train_model():
    if not os.path.exists(DATASET_DIR):
        setup_directories()
        return

    # Check if there are images to train on
    subdirs = [d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))]
    total_images = sum([len(os.listdir(os.path.join(DATASET_DIR, sd))) for sd in subdirs])
    
    if total_images < 6:
        setup_directories()
        print("Not enough images in dataset folder. Please add at least 1-2 images in each class folder before training.")
        return

    print(f"Found {total_images} images across classes. Starting transfer learning...")

    # Data Augmentation & Generators
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest',
        validation_split=0.2  # 20% validation split
    )

    train_generator = train_datagen.flow_from_directory(
        DATASET_DIR,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training'
    )

    validation_generator = train_datagen.flow_from_directory(
        DATASET_DIR,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation'
    )

    # Save class indices
    class_indices = {v: k for k, v in train_generator.class_indices.items()}
    with open(CLASSES_PATH, 'w') as f:
        json.dump(class_indices, f, indent=4)
    print(f"Saved class mapping to '{CLASSES_PATH}'")

    # Load base pre-trained MobileNetV2
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False  # Freeze pre-trained weights

    # Add classification head
    x = tf.keras.layers.GlobalAveragePooling2D()(base_model.output)
    x = tf.keras.layers.Dense(128, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(len(train_generator.class_indices), activation='softmax')(x)

    model = tf.keras.Model(inputs=base_model.input, outputs=outputs)
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    # Train model
    model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=validation_generator,
        verbose=1
    )

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    model.save(MODEL_PATH)
    print(f"Custom model saved successfully at '{MODEL_PATH}'!")

if __name__ == "__main__":
    train_model()
