import os 
import json

def get_perms_folder_path():
    return os.path.join(os.path.join(os.path.dirname(__file__), '../'), 'perms')

def safe_load_json(path):
    if os.path.isfile(path):
        with open(path, 'r') as file:
            return json.load(file)
    return {}
