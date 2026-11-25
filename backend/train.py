import os
import json
import numpy as np

# Set Keras cache directory inside workspace to avoid permission issues
os.environ['KERAS_HOME'] = os.path.abspath(os.path.join("scratch", ".keras"))
os.makedirs(os.environ['KERAS_HOME'], exist_ok=True)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

TRAIN_DIR = os.path.join("dataset_curated", "train")
VAL_DIR = os.path.join("dataset_curated", "val")
TEST_DIR = os.path.join("dataset_curated", "test")

MODEL_H5_PATH = os.path.join("backend", "waste_classifier.h5")
MODEL_TFLITE_PATH = os.path.join("backend", "waste_classifier.tflite")
CLASSES_PATH = os.path.join("backend", "class_indices.json")
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs("backend", exist_ok=True)

IMAGE_SIZE = (224, 224)
BATCH_SIZE = 16
STAGE1_EPOCHS = 10
STAGE2_EPOCHS = 10

def build_data_generators():
    # Training: Data Augmentation + MobileNetV2 Preprocessing
    train_datagen = ImageDataGenerator(
        preprocessing_function=tf.keras.applications.mobilenet_v2.preprocess_input,
        rotation_range=25,
        width_shift_range=0.15,
        height_shift_range=0.15,
        shear_range=0.15,
        zoom_range=0.15,
        horizontal_flip=True,
        fill_mode='nearest'
    )

    # Validation: Strictly unaugmented, only preprocessing
    val_datagen = ImageDataGenerator(
        preprocessing_function=tf.keras.applications.mobilenet_v2.preprocess_input
    )

    train_gen = train_datagen.flow_from_directory(
        TRAIN_DIR,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        shuffle=True,
        seed=42
    )

    val_gen = val_datagen.flow_from_directory(
        VAL_DIR,
        target_size=IMAGE_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        shuffle=False
    )

    return train_gen, val_gen

def build_model(num_classes):
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False  # Freeze for Stage 1

    x = tf.keras.layers.GlobalAveragePooling2D(name='global_avg_pool')(base_model.output)
    x = tf.keras.layers.BatchNormalization(name='batch_norm_1')(x)
    x = tf.keras.layers.Dense(128, activation='relu', name='dense_128')(x)
    x = tf.keras.layers.Dropout(0.3, name='dropout_1')(x)
    outputs = tf.keras.layers.Dense(num_classes, activation='softmax', name='classification_head')(x)

    model = tf.keras.Model(inputs=base_model.input, outputs=outputs, name='EcoSort_MobileNetV2')
    return model, base_model

def train():
    print("--- ECOSORT PHASE 2: MODEL TRAINING ---")
    train_gen, val_gen = build_data_generators()
    num_classes = len(train_gen.class_indices)
    
    # Save class indices
    class_indices = {v: k for k, v in train_gen.class_indices.items()}
    with open(CLASSES_PATH, 'w') as f:
        json.dump(class_indices, f, indent=4)
    print(f"Class mapping saved to '{CLASSES_PATH}': {class_indices}")

    model, base_model = build_model(num_classes)
    
    # Callbacks
    checkpoint = ModelCheckpoint(
        MODEL_H5_PATH,
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    )
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=4,
        restore_best_weights=True,
        verbose=1
    )
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=2,
        min_lr=1e-6,
        verbose=1
    )

    # STAGE 1: Feature Extraction
    print("\n>>> STAGE 1: Training Classification Head (Base Frozen) <<<")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    history_stage1 = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=STAGE1_EPOCHS,
        callbacks=[checkpoint, reduce_lr],
        verbose=1
    )

    # STAGE 2: Fine-Tuning Top Layers
    print("\n>>> STAGE 2: Fine-Tuning Top Layers of MobileNetV2 <<<")
    base_model.trainable = True
    # Freeze bottom layers, fine-tune from layer 110 onwards
    for layer in base_model.layers[:110]:
        layer.trainable = False
    
    trainable_count = sum([tf.keras.backend.count_params(w) for w in model.trainable_weights])
    print(f"Trainable parameters in Stage 2: {trainable_count:,}")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    history_stage2 = model.fit(
        train_gen,
        validation_data=val_gen,
        epochs=STAGE2_EPOCHS,
        callbacks=[checkpoint, early_stop, reduce_lr],
        verbose=1
    )

    # Combine Histories
    acc = history_stage1.history['accuracy'] + history_stage2.history['accuracy']
    val_acc = history_stage1.history['val_accuracy'] + history_stage2.history['val_accuracy']
    loss = history_stage1.history['loss'] + history_stage2.history['loss']
    val_loss = history_stage1.history['val_loss'] + history_stage2.history['val_loss']

    history_dict = {
        'accuracy': [float(x) for x in acc],
        'val_accuracy': [float(x) for x in val_acc],
        'loss': [float(x) for x in loss],
        'val_loss': [float(x) for x in val_loss],
        'stage1_epochs': len(history_stage1.history['accuracy']),
        'stage2_epochs': len(history_stage2.history['accuracy'])
    }
    with open(os.path.join(REPORTS_DIR, 'training_history.json'), 'w') as f:
        json.dump(history_dict, f, indent=4)

    # Plot Training Graphs
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    epochs_range = range(1, len(acc) + 1)
    
    ax1.plot(epochs_range, acc, label='Training Accuracy', color='#2d6a4f', lw=2)
    ax1.plot(epochs_range, val_acc, label='Validation Accuracy', color='#52b788', lw=2, linestyle='--')
    ax1.axvline(x=len(history_stage1.history['accuracy']), color='gray', linestyle=':', label='Fine-Tuning Start')
    ax1.set_title('Training & Validation Accuracy', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Epochs')
    ax1.set_ylabel('Accuracy')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)

    ax2.plot(epochs_range, loss, label='Training Loss', color='#d90429', lw=2)
    ax2.plot(epochs_range, val_loss, label='Validation Loss', color='#f77f00', lw=2, linestyle='--')
    ax2.axvline(x=len(history_stage1.history['accuracy']), color='gray', linestyle=':', label='Fine-Tuning Start')
    ax2.set_title('Training & Validation Loss', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Epochs')
    ax2.set_ylabel('Loss (Categorical Crossentropy)')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    curves_path = os.path.join(REPORTS_DIR, 'training_curves.png')
    plt.savefig(curves_path, dpi=300)
    plt.close()
    print(f"Training curves saved to '{curves_path}'")

    # Convert to TFLite (LiteRT format)
    print("\n>>> Exporting Model to LiteRT (TFLite) <<<")
    # Load best weights
    best_model = tf.keras.models.load_model(MODEL_H5_PATH)
    converter = tf.lite.TFLiteConverter.from_keras_model(best_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()

    with open(MODEL_TFLITE_PATH, 'wb') as f:
        f.write(tflite_model)
    tflite_size_mb = os.path.getsize(MODEL_TFLITE_PATH) / (1024 * 1024)
    print(f"Optimized LiteRT model saved at '{MODEL_TFLITE_PATH}' ({tflite_size_mb:.2f} MB)")

if __name__ == "__main__":
    train()
