from PIL import Image
import os

SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg'}
CUBEMAP_FACE_NAMES = ['', 'nx', 'pz', 'px', 'nz', 'ny', 'py']


import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()




def process_image(cubemap_image_num, img_path, out_path):
    with Image.open(img_path) as img:
        img = img.convert('RGB')
        img = img.resize((2048, 2048), Image.Resampling.LANCZOS)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        if cubemap_image_num == 5:
            img = img.transpose(Image.Transpose.ROTATE_90)
        elif cubemap_image_num == 6:
            img = img.transpose(Image.Transpose.ROTATE_270)

        img.save(
            out_path,
            'WEBP',
            quality=95,
            method=6,
            lossless=False,
        )


def process_cubemap_image_folder(cubemap_image_folder, in_dir_name, out_dir_name):
    """
    Process all cubemap images in a folder.
    """
    folder_path = os.path.join(in_dir_name, cubemap_image_folder)
    out_folder_path = os.path.join(out_dir_name, cubemap_image_folder)
    os.makedirs(out_folder_path, exist_ok=True)

    for image_file in os.listdir(folder_path):
        name, ext = os.path.splitext(image_file)
        if ext.lower() not in SUPPORTED_EXTS:
            print(f"Skipping {image_file}: unsupported file type.")
            continue

        try:
            num = int(name.split('#')[-1]) if '#' in name else -1
        except ValueError:
            print(f"Skipping {image_file}: invalid image name format.")
            continue

        if num not in range(1, 7):
            print(f"Skipping {image_file}: {num} invalid image name format.")
            continue

        img_path = os.path.join(folder_path, image_file)
        out_path = os.path.join(out_folder_path, f"{CUBEMAP_FACE_NAMES[num]}.webp")
        
        if os.path.isfile(out_path):
            print(f"Image exists {img_path} -> {out_path}...")
            continue

        print(f"Processing {img_path} -> {out_path}...")
        process_image(num, img_path, out_path)

def process_renders(render_folder, processed_folder):
    
    if not os.path.isdir(render_folder):
        print("Render folder does not exist")
        return
    os.makedirs(processed_folder, exist_ok=True)

    for cube_map_image_folder in os.listdir(render_folder):
        full_path = os.path.join(render_folder, cube_map_image_folder)
        if os.path.isdir(full_path):
            process_cubemap_image_folder(cube_map_image_folder, render_folder, processed_folder)


if __name__ == "__main__":
    parent_dir = filedialog.askdirectory(title="Select main folder")
    if not parent_dir:
        print("No input directory selected.")
        exit(1)
    render_dir = os.path.join(parent_dir, "renders")
    if not os.path.isdir(render_dir):
        print(f"Render directory does not exist: {render_dir}")
        exit(1)
    processed_dir = os.path.join(parent_dir, "processed_images")
    process_renders(render_dir, processed_dir)
