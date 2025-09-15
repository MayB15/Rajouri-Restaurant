"""
Common utilities for UE5 level data extraction
Shared functions for extracting floor, room, and panorama point data
"""

import unreal
import os, sys
import json
import tkinter as tk
from tkinter import filedialog

common_dir = os.path.dirname(os.path.abspath(__file__))
if common_dir not in sys.path:
    sys.path.append(common_dir)

from render_queue_validation import validate_movie_render_queue

# Constants for data extraction
IMAGE_EXTENSION = ".webp"
FLOOR_BLUEPRINT_PATH = "/Game/render_utils/BP/BP_Floor"
ROOM_BLUEPRINT_PATH = "/Game/render_utils/BP/BP_Room" 
PANO_POINT_BLUEPRINT_PATH = "/Game/render_utils/BP/BP_PanoPoint"

# Time of day and furnishing options
TIME_OF_DAY_OPTIONS = ["day", "night"]
FURNISHING_OPTIONS = ["furnished", "unfurnished"]
IMAGE_DIRECTIONS = "pn"
IMAGE_AXES = "xyz"

DEFAULT_RENDER_DIR = "processed_images"
CDN_BASE_URL = "https://cdn.spatium360.in/tour/"

class UE5DataExtractor:
    """Common utilities for UE5 level data extraction"""
    
    def __init__(self):
        # Initialize subsystems
        self.les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        
        # Load blueprint classes
        self.floor_class = unreal.load_asset(FLOOR_BLUEPRINT_PATH).generated_class()
        self.room_class = unreal.load_asset(ROOM_BLUEPRINT_PATH).generated_class()
        self.pano_point_class = unreal.load_asset(PANO_POINT_BLUEPRINT_PATH).generated_class()
    
    def get_enumerated_actors_of_class(self, bp_class, all_actors=None):
        """
        Get all actors of a specific blueprint class, sorted by label
        
        Args:
            bp_class: The blueprint class to filter by
            all_actors: List of all actors (if None, will fetch from level)
            
        Returns:
            enumerate: Enumerated list of sorted actors
        """
        if all_actors is None:
            all_actors = self.eas.get_all_level_actors()
            
        return enumerate(sorted([actor for actor in all_actors if actor.get_class() == bp_class], 
                               key=lambda a: a.get_actor_label()))
    
    def get_actor_editor_property(self, actor, prop: str):
        """
        Safely get an editor property from an actor
        
        Args:
            actor: The actor to get the property from
            prop: Property name to retrieve
            
        Returns:
            Property value or None if not found
        """
        try:
            return actor.get_editor_property(prop)
        except Exception as e:
            unreal.log_warning(f"Failed to get property '{prop}' from actor {actor.get_actor_label()}: {e}")
            return None
    
    def get_three_coords(self, pano_actor, height, connection_actor):
        """
        Calculate 3D coordinates for marker positioning
        
        Args:
            pano_actor: The panorama point actor
            height: Height offset for the panorama
            connection_actor: The connected panorama point
            
        Returns:
            dict: x, y, z coordinates
        """
        v = connection_actor.get_actor_location() - pano_actor.get_actor_location() - unreal.Vector(0, 0, height)
        return {
            "x": -v.x,
            "y": v.z,
            "z": -v.y,
        }
    
    def collect_floor_data(self, all_actors=None, floor_id_offset=0):
        """
        Collect data from all floor actors in the level
        
        Args:
            all_actors: List of all actors (if None, will fetch from level)
            floor_id_offset: ID offset for floor numbering
            
        Returns:
            dict: Floor data keyed by actor reference
        """
        floor_data = {}
        
        for i, floor in self.get_enumerated_actors_of_class(self.floor_class, all_actors):
            fl_data = {
                "floor_id": i + floor_id_offset,
                "floor_name": self.get_actor_editor_property(floor, 'FloorName'),
                "Main_Room": self.get_actor_editor_property(floor, "MainRoom"),
                "label": ""
            }
            floor_data[floor] = fl_data
            unreal.log(f"Collected floor data: {floor.get_actor_label()}")
        
        return floor_data
    
    def collect_room_data(self, all_actors=None, room_id_offset=0):
        """
        Collect data from all room actors in the level
        
        Args:
            all_actors: List of all actors (if None, will fetch from level)
            room_id_offset: ID offset for room numbering
            
        Returns:
            dict: Room data keyed by actor reference
        """
        room_data = {}
        
        for i, room in self.get_enumerated_actors_of_class(self.room_class, all_actors):
            r_data = {
                "Room_ID": i + room_id_offset,
                "Room_Name": self.get_actor_editor_property(room, 'RoomName'),
                "Floor": self.get_actor_editor_property(room, "Floor"),
                "Location": room.get_actor_location(),
                "Main_Panorama": self.get_actor_editor_property(room, "MainPanorama")
            }
            room_data[room] = r_data
            unreal.log(f"Collected room data: {room.get_actor_label()}")
        
        return room_data
    
    def collect_pano_point_data(self, level_names, all_actors=None, pano_id_offset=0):
        """
        Collect data from all panorama point actors in the level
        
        Args:
            all_actors: List of all actors (if None, will fetch from level)
            pano_id_offset: ID offset for panorama point numbering
            
        Returns:
            dict: Panorama point data keyed by actor reference
        """
        pano_point_data = {}
        
        for i, pano in self.get_enumerated_actors_of_class(self.pano_point_class, all_actors):
            p_data = {
                "PanoPoint_ID": i + pano_id_offset,
                "PanoName": pano.get_actor_label(),
                "level_names": level_names,
                "Room": self.get_actor_editor_property(pano, "Room"),
                "Height": self.get_actor_editor_property(pano, "Height"),
                "defaultRotation": self.get_actor_editor_property(pano, "defaultRotation"),
                "2WayConnections": self.get_actor_editor_property(pano, "2WayConnections"),
                "1WayConnections": self.get_actor_editor_property(pano, "1WayConnections")
            }
            pano_point_data[pano] = p_data
            unreal.log(f"Collected pano point data: {pano.get_actor_label()}")
        
        return pano_point_data
    
    def collect_all_level_set_data(self, level_names, floor_id_offset=0, room_id_offset=0, pano_id_offset=0):
        """
        Collect all level data (floors, rooms, panorama points) in one pass
        
        Args:
            floor_id_offset: ID offset for floor numbering
            room_id_offset: ID offset for room numbering  
            pano_id_offset: ID offset for panorama point numbering
            
        Returns:
            tuple: (floor_data, room_data, pano_point_data)
        """
        unreal.log("Starting level data collection...")
        
        # Get all actors once for efficiency
        all_actors = self.eas.get_all_level_actors()
        
        # Collect data for each actor type
        floor_data = self.collect_floor_data(all_actors, floor_id_offset)
        room_data = self.collect_room_data(all_actors, room_id_offset)
        pano_point_data = self.collect_pano_point_data(level_names, all_actors, pano_id_offset)
        
        unreal.log(f"Level data collection complete: {len(floor_data)} floors, {len(room_data)} rooms, {len(pano_point_data)} pano points")
        
        return floor_data, room_data, pano_point_data

    

    def generate_image_data_structure(self, pano_name, level_names, processed_render_dir=DEFAULT_RENDER_DIR):
        """
        Generate the nested image data structure for a panorama point
        
        Args:
            room_name: Name of the room
            pano_identifier: Panorama point identifier
            processed_render_dir: Base directory for processed renders
            
        Returns:
            dict: Nested image data structure
        """
        image_data = {}
        unreal.log(f"Generating image data structure for panorama '{level_names}'")
        for tod in TIME_OF_DAY_OPTIONS:
            image_data[tod] = {}
            for fur in FURNISHING_OPTIONS:
                image_data[tod][fur] = {}
                lc = (tod[0]+fur[0]).upper()
                ln = level_names[lc]
                for im_d in IMAGE_DIRECTIONS:
                    for im_ax in IMAGE_AXES:
                        image_key = f"{im_d}{im_ax}"
                        image_path = f"{processed_render_dir}/{ln}_{pano_name}_{lc}/{image_key}{IMAGE_EXTENSION}"
                        image_data[tod][fur][image_key] = image_path
        
        return image_data
    
    def process_panorama_data(self, floor_data, room_data, pano_point_data, floor_entries = [], room_entries = [], pano_entries = [], marker_entries = [], processed_render_dir=DEFAULT_RENDER_DIR):
        """
        Export collected data to JSON files
        
        Args:
            data_folder_path: Output directory for JSON files
            floor_data: Collected floor data
            room_data: Collected room data
            pano_point_data: Collected panorama point data
            processed_render_dir: Directory containing processed renders
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            # Process floor data
            for floor,data  in floor_data.items():
                floor_data[floor]["floor_map"] = os.path.join( 
                    "otherAssets/Maps", 
                    f"{floor_data[floor]['floor_id']}.jpeg"
                )
                fl_data = {
                "floor_id": data["floor_id"],
                "floor_name": data["floor_name"],
                "floor_map": "/fallback/map_not_found.jpeg",
                "main_room_id": room_data[floor_data[floor]["Main_Room"]]["Room_ID"] if floor_data[floor]["Main_Room"] else -1,
                "label": data.get("label", ""),
            }
                floor_entries.append(fl_data)
            
            # Process room data
            for room, data in room_data.items():
                room_entry = {
                    "room_id": data["Room_ID"],
                    "room_name": data["Room_Name"],
                    "main_panorama_id": pano_point_data[data["Main_Panorama"]]["PanoPoint_ID"] if data["Main_Panorama"] else -1,
                    "position": {
                        "x": data["Location"].x,
                        "y": data["Location"].y,
                    },
                    "floor_id": floor_data[data["Floor"]]["floor_id"] if data["Floor"] else -1,
                }
                room_entries.append(room_entry)
            
            # Process panorama point data

            marker_count = len(marker_entries)
            
            for pano, data in pano_point_data.items():
                unreal.log(f"Processing panorama point: {data}")
                pano_entry = {
                    "panorama_id": data["PanoPoint_ID"],
                    "default_rotation": data["defaultRotation"],
                    "image_data": self.generate_image_data_structure(
                        data["PanoName"],
                        data["level_names"],
                        processed_render_dir
                    ),
                    "room_id": room_data[data["Room"]]["Room_ID"] if data["Room"] else -1,
                }
                pano_entries.append(pano_entry)
                
                # Process connections for markers
                
                connections = list(data.get("2WayConnections", [])) + list(data.get("1WayConnections", []))
                
                for connection in connections:
                    try:
                        marker_entry = {
                            "marker_id": marker_count,
                            "start_panorama_id": data["PanoPoint_ID"],
                            "position": self.get_three_coords(pano, data["Height"], connection),
                            "target_panorama_id": pano_point_data[connection]["PanoPoint_ID"],
                        }
                        marker_entries.append(marker_entry)
                        marker_count += 1
                    except Exception as e:
                        unreal.log_error(f"Error processing connection for pano {data['PanoPoint_ID']} to {connection}: {e}")
        except Exception as e:
            unreal.log_error(f"Failed to export panorama data: {e}")
        
        return floor_entries, room_entries, pano_entries, marker_entries

    def write_json_files(self, folder_path, floor_json, room_json, pano_json, marker_json):
        json_files = [
            ("floor_data.json", floor_json),
            ("room_data.json", room_json), 
            ("pano_data.json", pano_json),
            ("marker_data.json", marker_json)
        ]
        

        
        os.makedirs(os.path.join(folder_path, "data"), exist_ok=True)
        for filename, data_dict in json_files:
            output_path = os.path.join(folder_path,"data", filename)
            with open(output_path, "w") as f:
                json.dump(data_dict, f, indent=4)
            unreal.log(f"Data exported to {output_path}")
        
        return True
            
        

    def collect_data_from_level_set_dicts_and_export(self,level_set_dict, folder_path, processed_render_dir=DEFAULT_RENDER_DIR):
        """
        Collect all level data and export to JSON files
        
        Args:
            data_folder_path: Output directory for JSON files
            floor_id_offset: ID offset for floor numbering
            room_id_offset: ID offset for room numbering  
            pano_id_offset: ID offset for panorama point numbering
            
        Returns:
            bool: True if export successful, False otherwise
        """

        unreal.log("Starting level data collection...")
        floor_entries, room_entries, pano_entries, marker_entries = [], [], [], []
        for lsd in level_set_dict.values():
            lvl_dict = {v[1]:v[2] for v in lsd}
            lvl_df = lvl_dict["DF"]
            level_name = lvl_df.split("/")[-1]
            lvl_dict = {k:v.split("/")[-1].split(".")[0] for k,v in lvl_dict.items()}
            unreal.log(f"Processing level: {level_name}")
            if self.les.load_level(lvl_df):
                unreal.log(f"Level {level_name} loaded successfully")

            # Collect all level data
            
            floor_data, room_data, pano_point_data = self.collect_all_level_set_data(lvl_dict, len(floor_entries), len(room_entries), len(pano_entries))
            floor_entries, room_entries, pano_entries, marker_entries = self.process_panorama_data(
                floor_data, room_data, pano_point_data, 
                floor_entries, room_entries, pano_entries, marker_entries, processed_render_dir
            )


        unreal.log(f"Collected {len(floor_entries)} floors, {len(room_entries)} rooms, {len(pano_entries)} pano points")
        
        # Export collected data to JSON files
        self.write_json_files(
            folder_path, 
            floor_entries, 
            room_entries, 
            pano_entries, 
            marker_entries
        )
        return 


if __name__ == "__main__":
    # Example usage when run directly
    extractor = UE5DataExtractor()

    root = tk.Tk()
    root.withdraw()
    data_folder_path = filedialog.askdirectory(title="Select Output Folder")
    if not data_folder_path:
        unreal.log_warning("No folder selected. Exiting.")
        exit()
    
    _, _, level_set_dict = validate_movie_render_queue()
    extractor.collect_data_from_level_set_dicts_and_export(level_set_dict, data_folder_path)
    # For testing, you would need to specify an output directory
    # extractor.export_panorama_data("C:/output", floor_data, room_data, pano_point_data)
    
    unreal.log("Data extraction completed. Use export_panorama_data() to save to files.")
