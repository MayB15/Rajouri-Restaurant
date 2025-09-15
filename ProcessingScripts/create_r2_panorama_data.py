import os, sys
import json
import tkinter as tk
from tkinter import filedialog
from pathlib import Path


def update_panorama_json_file(project_dir: Path):
    """
    Update the JSON file with the cubemap image URLs on R2 from local paths.
    """

    if not project_dir.exists():
        print(f"Project directory {project_dir} does not exist.")
        return
    
    data_dir = project_dir / "data"

    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist.")
        return 
    
    panorama_json_path = data_dir / "pano_data.json"
    if not panorama_json_path.exists():
        print(f"panorama.json file does not exist in {data_dir}.")
        return
    
    cubemap_upload_json = data_dir / "cubemap_upload_map.json"
    if not cubemap_upload_json.exists():
        print(f"cubemap_upload_map.json file does not exist in {data_dir}.")
        return
    
    with open(cubemap_upload_json, 'r') as f:
        cubemap_upload_map = json.load(f)

    with open(panorama_json_path, 'r') as f:
        panorama_data = json.load(f)

    def replace_paths(obj):
        if isinstance(obj, dict):
            return {k: replace_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_paths(item) for item in obj]
        elif isinstance(obj, str):
            # Replace if the string matches a local path in cubemap_upload_map
            return cubemap_upload_map.get(obj, obj)
        else:
            return obj

    updated_panorama_data = replace_paths(panorama_data)

    r2_panorama_json = data_dir / "r2_panorama.json"
    with open(r2_panorama_json, 'w') as f:
        json.dump(updated_panorama_data, f, indent=2)

    


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    project_dir = Path(filedialog.askdirectory(title="Select the project directory"))
    if not project_dir:
        print("No project directory selected. Exiting.")
        sys.exit(1)

    update_panorama_json_file(project_dir)
    print(f"Updated panorama.json file in {project_dir / 'data'} with R2 URLs.")