import unreal # type: ignore
import os, datetime, json
#Floor Data - ID, details inputed manually
#Room - ID, Floor ID, Position from Map, Main Panorama
#PanoPoint - ID, Room ID, Images  | World Coordinates, Height
#Marker - From Pano, To Pano | World Coordinates?( Coordinates of To Pano for now)



import tkinter as tk
from tkinter import filedialog


# Initialize Tkinter root
root = tk.Tk()
root.withdraw()  # Hide the root window

folder_path = filedialog.askdirectory(title="Select the folder containing panorama data")   


print(f"Selected folder: {folder_path}")



les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

all_actors = unreal.EditorLevelLibrary.get_all_level_actors()

floor_bp, room_bp, pano_point_bp = [unreal.load_asset("/Game/render_utils/BP/"+blueprint_name).generated_class()  for blueprint_name in ["BP_Floor", "BP_Room", "BP_PanoPoint"]]

def getActorsOfClass(bp):
    return enumerate(sorted([actor for actor in all_actors if actor.get_class() == bp],key = lambda a: a.get_actor_label()))

def getActorEditorProperty(a,prop: str):
    try:
        return a.get_editor_property(prop)
    except:
        return None
    
def print_dict(d,tabs=1):
    for k,v in d.items():
        print("\t"*tabs, k," : ",v)
    print("_"*20)


p_data = {}
for i, pano in getActorsOfClass(pano_point_bp):
    p_data[les.get_current_level().get_name().split("/")[-1]+"_"+pano.get_actor_label()] = getActorEditorProperty(pano, "PanoIdentifier")



print("_"*20)
print("_"*20)


with open(os.path.join(folder_path,"pano.json"), "w") as f:
    json.dump(p_data, f, indent=4)

#with open("D:\\360WebPlatform\\public\\data\\bhatia.json", "w") as f:
#    json.dump({"floors": floor_json, "rooms": room_json, "panoramas": pano_json, "markers": marker_json}, f, indent=4)