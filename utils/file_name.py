import os
from pathlib import Path

def get_all_file_paths(folder_path, prefix=None, suffix=None):
    file_paths = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_paths.append(os.path.join(root, file))

    if prefix is not None:
        file_paths = [p for p in file_paths if p.startswith(prefix)]
    if suffix is not None:
        file_paths = [p for p in file_paths if p.endswith(suffix)]
    
    return sorted(file_paths)

def list_dir(dir):
    path_list = os.listdir(dir)
    path_list = [os.path.join(dir, n) for n in path_list]
    return sorted(path_list)

def basename_without_suffix(path):
    base_name = Path(path).stem  # Get the base name without the suffix
    return base_name

def completed_or_not(file_path, dir):
    target_name = basename_without_suffix(file_path)
    file_names = os.listdir(dir)
    for file_name in file_names:
        if target_name == basename_without_suffix(file_name):
            return os.path.join(dir, file_name)
    return None