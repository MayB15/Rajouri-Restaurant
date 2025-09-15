import unreal  # type: ignore
import os
import datetime
import json
import tkinter as tk
from tkinter import filedialog
image_ext = ".jpeg"

floor_bp, room_bp, pano_point_bp = [
    unreal.load_asset("/Game/render_utils/BP/" + blueprint_name).generated_class()
    for blueprint_name in ["BP_Floor", "BP_Room", "BP_PanoPoint"]
]


def getActorsOfClass(bp, all_actors):
    return enumerate(sorted([actor for actor in all_actors if actor.get_class() == bp], key=lambda a: a.get_actor_label()))

def getActorEditorProperty(a, prop: str):
    try:
        return a.get_editor_property(prop)
    except Exception:
        return None

def print_dict(d, tabs=1):
    for k, v in d.items():
        print("\t" * tabs, k, " : ", v)
    print("_" * 20)

def getThreeCoords(pano, height, con):
    v = con.get_actor_location() - pano.get_actor_location() - unreal.Vector(0, 0, height)
    return {
        "x": -v.x,
        "y": v.z,
        "z": -v.y,
    }

def collect_level_data(folder_path, floorData = {}, roomData = {}, panoPointData = {}):
    # Initialize Tkinter root
    
    print(f"Selected folder: {folder_path}")

    # Remove exit() to allow script to continue
    # exit()

    # Setup

    floor_id_inc = 0
    room_id_inc = 0
    pano_id_inc = 0   

    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()


    # Collect floor data
    for i, floor in getActorsOfClass(floor_bp, all_actors):
        fl_data = {}
        fl_data["floor_id"] = i + floor_id_inc
        fl_data["floor_name"] = getActorEditorProperty(floor, 'FloorName')
        fl_data["label"] = ""
        floorData[floor] = fl_data

    # Collect room data
    for i, room in getActorsOfClass(room_bp, all_actors):
        r_data = {}
        r_data["Room_ID"] = i + room_id_inc
        r_data["Room_Name"] = getActorEditorProperty(room, 'RoomName')
        r_data["Floor"] = getActorEditorProperty(room, "Floor")
        r_data["Location"] = room.get_actor_location(),
        r_data["Main_Panorama"] = getActorEditorProperty(room, "MainPanorama")
        roomData[room] = r_data

    # Collect pano point data
    for i, pano in getActorsOfClass(pano_point_bp, all_actors):
        p_data = {}
        p_data["PanoPoint_ID"] = i + pano_id_inc
        p_data["PanoIdentifier"] = getActorEditorProperty(pano, "PanoIdentifier")
        p_data["Room"] = getActorEditorProperty(pano, "Room")
        p_data["Height"] = getActorEditorProperty(pano, "Height")
        p_data["defaultRotation"] = getActorEditorProperty(pano, "defaultRotation")
        p_data["2WayConnections"] = getActorEditorProperty(pano, "2WayConnections")
        p_data["1WayConnections"] = getActorEditorProperty(pano, "1WayConnections")
        panoPointData[pano] = p_data

    return floorData, roomData, panoPointData


def write_pano_data(data_folder_path, floorData, panoPointData, roomData, processed_render_dir):
    for floor in floorData:
        floorData[floor]["floor_map"] = os.path.join(os.path.dirname(data_folder_path), "/otherAssets/Maps", f"{floor['floor_id']}.jpeg")
    floor_json = list(floorData.values())
    room_json = []

    for room, data in roomData.items():
        room_json.append(
            {
                "room_id": data["Room_ID"],
                "room_name": data["Room_Name"],
                "main_panorama_id": panoPointData[data["Main_Panorama"]]["PanoPoint_ID"] if data["Main_Panorama"] else -1,
                "position": {
                    "x": data["Location"][0].x,
                    "y": data["Location"][0].y,
                },
                "floor_id": floorData[data["Floor"]]["floor_id"] if data["Floor"] else -1,
            }
        )

    pano_json = []
    marker_json = []

    for pano, data in panoPointData.items():
        pano_json.append(
            {
                "panorma_id": data["PanoPoint_ID"],
                "default_rotation": data["defaultRotation"],
                "image_data":
                    {tod:
                        {fur:
                            {
                                f"{im_d}{im_ax}":
                                    f"{processed_render_dir}/{roomData[data['Room']]['Room_Name']}_{data['PanoIdentifier']}_{'d'}_{'f' if (fur == 'furnished') else 'u'}/{im_d}{im_ax}{image_ext}"
                                for im_d in "pn" for im_ax in "xyz"}
                        for fur in ["furnished", "unfurnished"]}
                    for tod in ["day", "night"]
                    },
                "room_id": roomData[data["Room"]]["Room_ID"] if data["Room"] else -1,
            }
        )


        marker_count = 0
        for con in list(data["2WayConnections"]) + list(data["1WayConnections"]):
            try:
                marker_json.append({
                    "marker_id": marker_count,
                    "panorma_id": data["PanoPoint_ID"],
                    "position": getThreeCoords(pano, data["Height"], con),
                    "target_panorama_id": panoPointData[con]["PanoPoint_ID"],
                })
                marker_count += 1
            except Exception as e:
                print(f"Error processing connection for pano {data['PanoIdentifier']} to {con}: {e}")
    
    for file, dict in (("floor_data.json", floor_json), ("room_data.json", room_json), ("pano_data.json", pano_json), ("marker_data.json", marker_json)):
        outpath = os.path.join(data_folder_path, file)
        with open(outpath, "w") as f:
            json.dump(dict, f, indent=4)

        print(f"Data exported to {outpath}")

if __name__ == "__main__":

    root = tk.Tk()
    root.withdraw()  # Hide the root window

    fp = filedialog.askdirectory(title="Select the folder containing panorama data")
    collect_level_data(fp)