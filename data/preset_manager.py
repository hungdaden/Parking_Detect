import os
import json
from datetime import datetime

PRESETS_DIR = "presets"
if not os.path.exists(PRESETS_DIR):
    os.makedirs(PRESETS_DIR)


class PresetManager:
    """Class quản lý việc lưu, đọc, liệt kê và xóa các file preset khoanh vùng ô đỗ."""

    @staticmethod
    def get_preset_list():
        files = [f for f in os.listdir(PRESETS_DIR) if f.endswith('.json') and f != 'app_config.json']
        files.sort(key=lambda x: os.path.getmtime(os.path.join(PRESETS_DIR, x)), reverse=True)
        return [f.replace('.json', '') for f in files]

    @staticmethod
    def load_preset(name):
        p = os.path.join(PRESETS_DIR, name + ".json")
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        polygons = [list(map(tuple, poly)) for poly in data.get("polygons", [])]
        return polygons

    @staticmethod
    def save_preset(name, polygons):
        data = {
            "name": name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "polygons": [list(map(list, poly)) for poly in polygons]
        }
        p = os.path.join(PRESETS_DIR, name + ".json")
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return p

    @staticmethod
    def delete_preset(name):
        p = os.path.join(PRESETS_DIR, name + ".json")
        if os.path.exists(p):
            os.remove(p)
            return True
        return False
