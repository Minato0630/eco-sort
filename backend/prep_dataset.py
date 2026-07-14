import os
import shutil

# Paths
WORKSPACE_DIR = r"C:\Users\pandi\PROJECTS\waste-sorting-ml"
IMAGES_DIR = os.path.join(WORKSPACE_DIR, "IMAGES")
DATASET_DIR = os.path.join(WORKSPACE_DIR, "dataset")
ARTIFACTS_DIR = r"C:\Users\pandi\.gemini\antigravity\brain\bbecce9e-a903-471e-8a6a-5aadeb4a539b"

# Define classes
CLASSES = ["Organic", "Plastic", "Paper", "Metal", "E-Waste", "General"]

# Create directories
for c in CLASSES:
    os.makedirs(os.path.join(DATASET_DIR, c), exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Original IMAGES mapping
ORIGINAL_MAPPING = {
    "Newspaper.jpg": "Paper",
    "Plastic carry bag.jpg": "Plastic",
    "Waterbottle.jpg": "Plastic",
    "apple_core.jpg": "Organic",
    "banana peel.jpg": "Organic",
    "cardboard": "Paper",
    "cardboard_box.jpg": "Paper",
    "circuit board.jpg": "E-Waste",
    "food tins.jpg": "Metal",
    "food wrapper.jpg": "General",
    "fruit scraps.jpg": "Organic",
    "left over food.jpg": "Organic",
    "mobile wate.jpg": "E-Waste",
    "soda_can.jpg": "Metal",
    "soft drink.jpg": "Plastic",
}

# Copy original images to dataset/
print("Copying original images to dataset subfolders...")
for filename, category in ORIGINAL_MAPPING.items():
    src_path = os.path.join(IMAGES_DIR, filename)
    dest_path = os.path.join(DATASET_DIR, category, filename)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)
        print(f"Copied: IMAGES/{filename} -> dataset/{category}/{filename}")
    else:
        print(f"Warning: Original file not found at {src_path}")

# New images from artifacts mapping
NEW_IMAGES = {
    "rotting_orange_1782187524525.png": ("Organic", "rotting_orange.jpg"),
    "decaying_banana_peel_1782187537030.png": ("Organic", "decaying_banana_peel.jpg"),
    "crushed_plastic_straws_1782187551875.png": ("Plastic", "crushed_plastic_straws.jpg"),
    "plastic_cup_lid_1782187575657.png": ("Plastic", "plastic_cup_lid.jpg"),
    "crumpled_office_paper_1782187593704.png": ("Paper", "crumpled_office_paper.jpg"),
    "crushed_soda_can_1782187618173.png": ("Metal", "crushed_soda_can.jpg"),
    "broken_tv_remote_1782187649885.png": ("E-Waste", "broken_tv_remote.jpg"),
    "loose_aa_batteries_1782187686324.png": ("E-Waste", "loose_aa_batteries.jpg"),
    "broken_ceramic_pieces_1782187716471.png": ("General", "broken_ceramic_pieces.jpg"),
    "empty_chips_bag_1782187754949.png": ("General", "empty_chips_bag.jpg"),
}

print("\nCopying new generated images from artifacts to IMAGES/ and dataset/...")
for art_name, (category, final_name) in NEW_IMAGES.items():
    src_path = os.path.join(ARTIFACTS_DIR, art_name)
    
    # 1. Copy to IMAGES/
    img_dest_path = os.path.join(IMAGES_DIR, final_name)
    
    # 2. Copy to dataset/Category/
    dataset_dest_path = os.path.join(DATASET_DIR, category, final_name)
    
    if os.path.exists(src_path):
        shutil.copy2(src_path, img_dest_path)
        shutil.copy2(src_path, dataset_dest_path)
        print(f"Copied new sample: {art_name} -> IMAGES/{final_name} & dataset/{category}/{final_name}")
    else:
        print(f"Warning: Artifact file not found at {src_path}")

print("\nDataset preparation completed successfully!")
