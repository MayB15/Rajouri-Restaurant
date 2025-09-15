from PIL import Image
import os

img_dir = input('Enter the directory of the image: ')
img_dir = os.path.join(os.getcwd(), img_dir)

if not os.path.exists(img_dir):
    print("Directory does not exist. Please check the path.")
    exit()

op_dir = os.path.join(img_dir+'_webp')
if not os.path.exists(op_dir):
    os.makedirs(op_dir)
else:
    print("Output directory already exists. Files maybe rewritten.")


for img_file in os.listdir(img_dir):
    if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
        img_path = os.path.join(img_dir, img_file)
        img = Image.open(img_path)
        img = img.convert('RGB')
        base_name = os.path.splitext(img_file)[0]
        output_file = os.path.join(op_dir, base_name + '.webp')
        img.save(output_file, 'WEBP', 
                 quality=95,           # Good balance of quality/size
                 method=6,             # Default - good speed/compression balance
                 lossless=False,       # Use lossy for smaller files
                 )
