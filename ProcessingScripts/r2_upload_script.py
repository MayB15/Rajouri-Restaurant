#!/usr/bin/env python3
"""
Upload images to Cloudflare R2 and generate URL mappings
"""

import os
import json
import boto3
import mimetypes
from pathlib import Path
from typing import Dict, List, Tuple
from botocore.exceptions import ClientError
import time
import tkinter as tk
from tkinter import filedialog
import hmac
import hashlib




root = tk.Tk()
root.withdraw()


SUPPORTED_EXTENSIONS = {'.webp'}
DATA_FILE_MAP = {
    "floor_data.json": "floor_data.json",
    "room_data.json": "room_data.json",
    "r2_panorama.json": "panorama_data.json",
    "marker_data.json": "marker_data.json",
    "r2_panorama_image_set_data.json": "panorama_image_sets.json",
}
class R2Uploader:
    BUCKET_NAME = "spatium360"

    def __init__(self):
        """Initialize R2 client with credentials from environment"""
        self.account_id = "5769c612a18adf0e11e156dc3581c867"
        self.access_key = "1c81dcc0921938cd7ba5480562dab1e7"
        self.secret_key = "f5c3c23a5033b522aaf07e024b16a5fee4d16046da71b0ec61e849dfca25c67f"
        
        if not all([self.account_id, self.access_key, self.secret_key]):
            raise ValueError(
                "Missing required environment variables:\n"
                "- CLOUDFLARE_ACCOUNT_ID\n"
                "- R2_ACCESS_KEY\n"
                "- R2_SECRET_KEY"
            )
        
        # Configure S3 client for R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='auto'
        )
        
        print(f"🔗 Connected to R2 with account: {self.account_id}")
    
    
    def assert_upload_image_file(self, local_path: Path, r2_key: str, subdir: List[str] = []) -> str:
        """
        Upload a single file to R2 and return the public URL.
        If subdir is provided as a list [a, b], the file will be uploaded to a/b/file.ext instead of file.ext.
        """
        # Adjust r2_key if subdir is provided
        r2_key = f"{"/".join(subdir)}/{r2_key}"

        cdn_url = f"https://cdn.spatium360.in/{r2_key}"
        
        try:
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(local_path))
            if not content_type:
                content_type = 'image/webp'  # Default to webp if unknown

            # Check if file exists and is identical (by size and SHA256)
            try:
                obj = self.s3_client.head_object(Bucket=R2Uploader.BUCKET_NAME, Key=r2_key)
                # Download remote file for comparison
                remote_file = self.s3_client.get_object(Bucket=R2Uploader.BUCKET_NAME, Key=r2_key)['Body'].read()
                remote_hash = hashlib.sha256(remote_file).hexdigest()
                with open(local_path, 'rb') as f:
                    local_data = f.read()
                    local_hash = hashlib.sha256(local_data).hexdigest()

                if remote_hash and remote_hash == local_hash:
                    print(f"⏩ Skipped (identical): {r2_key}")
                    return cdn_url
            except self.s3_client.exceptions.NoSuchKey:
                # File does not exist, proceed with upload
                print(f"🔄 File not found, uploading: {r2_key}")
                pass
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise

            # Upload file
            with open(local_path, 'rb') as file_data:
                local_hash = hashlib.sha256(file_data.read()).hexdigest()
                file_data.seek(0)
                self.s3_client.upload_fileobj(
                    file_data,
                    R2Uploader.BUCKET_NAME,
                    r2_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'ACL': 'public-read',
                        'Metadata': {'sha256': local_hash}
                    }
                )
            
            print(f"✅ Uploaded: {r2_key}")
            return cdn_url
            
        except ClientError as e:
            print(f"❌ Failed to upload {r2_key}: {e}")
            return ""
        except Exception as e:
            print(f"❌ Unexpected error uploading {r2_key}: {e}")
            return ""
    
    def assert_upload_image_batch(self, files: List[Tuple[Path, str, str]], batch_size: int = 10, subdir: List[str] = []) -> Dict[str, str]:
        """Upload files in batches with rate limiting"""
        url_mappings = {}
        total_files = len(files)
        success_count = 0
        
        print(f"📤 Starting upload of {total_files} files in batches of {batch_size}\n")
        
        for i in range(0, total_files, batch_size):
            batch = files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            print(f"📦 Processing batch {batch_num}/{total_batches}...")
            
            for local_path, r2_key, original_identifier in batch:
                cdn_url = self.assert_upload_image_file(local_path, r2_key, subdir=subdir)
                if cdn_url:
                    url_mappings[original_identifier] = cdn_url
                    success_count += 1
            
            # Rate limiting - small delay between batches
            if i + batch_size < total_files:
                time.sleep(1)
        
        print(f"\n🎉 Upload complete! {success_count}/{total_files} files uploaded successfully")
        return url_mappings
    
    def save_url_mappings(self, mappings: Dict[str, str], output_file: str = "url_mappings.json"):
        """Save URL mappings to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(mappings, f, indent=4)
        print(f"💾 URL mappings saved to: {output_file}")
    
    def verify_bucket_access(self) -> bool:
        """Verify that we can access the R2 bucket"""
        try:
            self.s3_client.head_bucket(Bucket=R2Uploader.BUCKET_NAME)
            print(f"✅ Bucket '{R2Uploader.BUCKET_NAME}' is accessible")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"❌ Bucket '{R2Uploader.BUCKET_NAME}' not found")
            elif error_code == '403':
                print(f"❌ Access denied to bucket '{R2Uploader.BUCKET_NAME}'")
            else:
                print(f"❌ Error accessing bucket: {e}")
            return False

    def upload_json_file(self, local_path: Path, r2_key: str, subdir: List[str] = []) -> str:
        """
        Upload a single JSON file to R2 and return the public URL.
        If subdir is provided as a list [a, b], the file will be uploaded to a/b/file.ext instead of file.ext.
        """
        # Adjust r2_key if subdir is provided
        r2_key = f"{"/".join(subdir)}/{r2_key}"

        cdn_url = f"https://cdn.spatium360.in/{r2_key}"
        
        try:
            # Determine content type
            content_type = 'application/json'  # Default to JSON
            if not local_path.suffix.lower() == '.json':
                raise ValueError("Invalid file type: Only JSON files are supported")
            # Upload file
            with open(local_path, 'rb') as file_data:
                local_hash = hashlib.sha256(file_data.read()).hexdigest()
                file_data.seek(0)
                self.s3_client.upload_fileobj(
                    file_data,
                    R2Uploader.BUCKET_NAME,
                    r2_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'ACL': 'public-read',
                        'Metadata': {'sha256': local_hash}
                    }
                )
            
            print(f"✅ Uploaded: {r2_key}")
            return cdn_url
            
        except ClientError as e:
            print(f"❌ Failed to upload {r2_key}: {e}")
            return ""
        except Exception as e:
            print(f"❌ Unexpected error uploading {r2_key}: {e}")
            return ""
        

    def delete_tour(self, tour_id: str) -> bool:
        """
        Delete a folder and all its contents from R2.

        """
        r2_folder = f"tour/{tour_id}/"
        try:
            # List all objects in the folder
            print(f"🗑️ Deleting folder '{r2_folder}' and its contents...")
            response = self.s3_client.list_objects_v2(Bucket=R2Uploader.BUCKET_NAME, Prefix=r2_folder)

            # Use paginator to handle large numbers of objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=R2Uploader.BUCKET_NAME,
                Prefix=r2_folder
            )
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        print(f"🗑️ Deleting object: {obj['Key']}")
                        self.s3_client.delete_object(Bucket=R2Uploader.BUCKET_NAME, Key=obj['Key'])
            print(f"✅ Successfully deleted folder '{r2_folder}' and its contents")
            
            return True
        except ClientError as e:
            print(f"❌ Error deleting folder '{r2_folder}': {e}")
            return False



def verify_connection(function):
    def wrapper(*args, **kwargs):
        print("🚀 Starting Cloudflare R2 image upload...\n")
        try:
            uploader = R2Uploader()
            if not uploader.verify_bucket_access():
                print("\n💡 Make sure your bucket exists and credentials are correct")
                return
            print("Connection established successfully!")
            return function( *args, uploader=uploader,**kwargs)
        except Exception as e:
            print(f"❌ Error during upload//: {e}")
            return 1
    return wrapper





@verify_connection
def image_upload_test(im_local_path, uploader = None):
    if uploader is None:
        return 1
    
    uploader.assert_upload_image_file(im_local_path,"test.webp",["folder","subfolder2"])
    return 0

@verify_connection
def upload_processed_images(tour_folder, tour_id, tour_data_token ,uploader = None):
    
    if uploader is None:
        print("Invalid Uploader")
        return
    if not os.path.isdir(tour_folder):
        print("Invalid tour dir")
        return
    
    dir = Path(tour_folder)
    data_dir = dir / "data"
    im_dir = dir / "processed_images"

    if not data_dir.exists():
        print(f"❌ Data directory does not exist: {data_dir}")
        return
    if not im_dir.exists():
        print(f"❌ Processed images directory does not exist: {im_dir}")
        return

    # Traverse im_dir for all .webp files
    webp_files = []
    for file_path in im_dir.rglob('*.webp'):
        if file_path.is_file():
            # r2_key is the relative path from im_dir, using forward slashes
            image_relative_path = str(file_path.relative_to(dir)).replace('\\', '/')
            r2_key = hmac.new(
                tour_data_token.encode('utf-8'),
                image_relative_path.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()[:16]
            webp_files.append((file_path, r2_key, image_relative_path))
    image_upload_map =  uploader.assert_upload_image_batch(webp_files,subdir=["tour", tour_id, "cubemap"])
    output_path = dir / "data" / "cubemap_upload_map.json"
    with open(output_path, "w") as f:
        json.dump(image_upload_map, f, indent=4)
    print(f"💾 Cubemap upload map saved to: {output_path}")

    print(f"Found {len(webp_files)} .webp files in {im_dir}")


@verify_connection
def upload_processed_data(tour_folder, tour_id, tour_data_token ,uploader = None):
    
    if uploader is None:
        print("Invalid Uploader")
        return
    if not os.path.isdir(tour_folder):
        print("Invalid tour dir")
        return
    
    dir = Path(tour_folder)
    data_dir = dir / "data"
    im_dir = dir / "processed_images"

    if not data_dir.exists():
        print(f"❌ Data directory does not exist: {data_dir}")
        return
    if not im_dir.exists():
        print(f"❌ Processed images directory does not exist: {im_dir}")
        return

    for local_file, upload_name in DATA_FILE_MAP.items():
        local_path = data_dir / local_file
        if not local_path.exists():
            print(f"❌ {local_file} does not exist in {data_dir}")
            continue

        cdn_url = uploader.upload_json_file(local_path, upload_name, subdir=["tour", tour_id, "data", tour_data_token])
        if cdn_url:
            print(f"✅ Uploaded {local_file} to {cdn_url}")
        else:
            print(f"❌ Failed to upload {local_file}")

@verify_connection
def delete_tour(tour_id, uploader = None):
    """
    Delete a tour and all its contents from R2.
    """
    if uploader is None:
        print("Invalid Uploader")
        return
    
    if not tour_id:
        print("No tour ID provided.")
        return

    if uploader.delete_tour(tour_id):
        print(f"✅ Tour '{tour_id}' deleted successfully")
    else:
        print(f"❌ Failed to delete tour '{tour_id}'")

def upload_images():

    """Main function to upload all images"""

    tour_folder = filedialog.askdirectory()
    if not tour_folder:
        print("No tour folder selected.")
        return

    tour_id = input("Enter tour ID: ")
    if not tour_id:
        print("No tour ID provided.")
        return

    tour_data_token = input("Enter tour data token: ")
    if not tour_data_token:
        print("No tour data token provided.")
        return
    upload_processed_images(tour_folder, tour_id, tour_data_token)

def upload_data():

    """Main function to upload all images"""

    tour_folder = filedialog.askdirectory()
    if not tour_folder:
        print("No tour folder selected.")
        return

    tour_id = input("Enter tour ID: ")
    if not tour_id:
        print("No tour ID provided.")
        return

    tour_data_token = input("Enter tour data token: ")
    if not tour_data_token:
        print("No tour data token provided.")
        return
    upload_processed_data(tour_folder, tour_id, tour_data_token)

def delete_tour_utility():
    """
    Main function to delete a tour and all its contents from R2.
    """
    tour_id = input("Enter tour ID to delete: ")
    if not tour_id:
        print("No tour ID provided.")
        return
    
    delete_tour(tour_id)

if __name__ == "__main__":
    upload_data()

