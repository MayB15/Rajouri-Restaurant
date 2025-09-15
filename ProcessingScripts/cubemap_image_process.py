from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()


main_dir = filedialog.askdirectory(title="Select a cubemap folder")

if not main_dir:
    print("No directory selected. Exiting.")
    exit()

if not os.path.exists(main_dir):
    print("Directory does not exist. Please check the path.")
    exit()

op_dir = filedialog.askdirectory(title="Select a output folder")
if not op_dir:
    print("No output directory selected. Exiting.")
    exit()

if not os.path.exists(op_dir):
    os.makedirs(op_dir)
else:
    if len(os.listdir(op_dir)) > 0:
        print("Output directory already exists and is not empty. Please choose a different directory or delete the existing one.")
        exit()




def cubemap_image_process(cubemap_image_folder,in_dir_name, out_dir_name):
    """
    Process a single cubemap image folder.
    """
    for image_file in os.listdir(os.path.join(in_dir_name, cubemap_image_folder)):

        cubemap_image_name, cubemap_image_ext = os.path.splitext(image_file)
        if cubemap_image_ext.lower() not in ['.png', '.jpg', '.jpeg']:
            print(f"Skipping {cubemap_image_folder}: unsupported file type.")
            return
        
        cubemap_image_num = int(cubemap_image_name.split('#')[-1]  if '#' in cubemap_image_name else -1)
        if cubemap_image_num not in range(1, 7):
            print(f"Skipping {cubemap_image_folder}: {cubemap_image_num} .invalid image name format.")
            return


        img_path = os.path.join(in_dir_name, cubemap_image_folder, image_file)
        print(f"Processing {img_path}...")
        
        img = Image.open(img_path)
        
        img = img.convert('RGB')
        img = img.resize((2048, 2048), Image.Resampling.LANCZOS)  # Resize to 2048x2048

        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if cubemap_image_num == 5:
            img = img.transpose(Image.Transpose.ROTATE_90)

        elif cubemap_image_num == 6:
            img = img.transpose(Image.Transpose.ROTATE_270)
        if not os.path.exists(out_dir_name):
            os.makedirs(out_dir_name)
        if not os.path.exists(os.path.join(out_dir_name, cubemap_image_folder)):
            os.makedirs(os.path.join(out_dir_name, cubemap_image_folder))

        output_file = os.path.join(out_dir_name, cubemap_image_folder,
                                   ['', 'nx', 'pz', 'px', 'nz', 'ny', 'py'][cubemap_image_num]
                                   + '.webp')
        img.save(output_file, 'WEBP', 
                quality=95,           # Good balance of quality/size
                method=6,             # Default - good speed/compression balance
                lossless=False,       # Use lossy for smaller files
                )
    

for cubemap_folder in os.listdir(main_dir):
    cubemap_image_process(cubemap_folder, main_dir, op_dir)
