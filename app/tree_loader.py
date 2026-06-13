import json

TREE_PATH = "tree.json"


def load_tree():
    with open(TREE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)