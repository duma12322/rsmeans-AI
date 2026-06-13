from app.tree_loader import load_tree
from app.tree_ai import choose_node

TREE = load_tree()


def get_children(path):
    node = TREE

    for p in path:
        node = node[p]["_children"]

    return node


def format_options(children):
    return [
        {
            "code": k,
            "name": v["_name"]
        }
        for k, v in children.items()
    ]


def select_level(question, path):

    children = get_children(path)
    options = format_options(children)

    options_text = "\n".join([
        f"{o['code']} - {o['name']}"
        for o in options
    ])

    print("\n" + "=" * 80)
    print("QUESTION:")
    print(question)

    print("\nCURRENT PATH:")
    print(" > ".join(path) if path else "ROOT")

    print("\nAVAILABLE OPTIONS:")
    for o in options:
        print(f"{o['code']} - {o['name']}")

    print("\nASKING AI...")

    raw = choose_node(question, options_text, path)

    print("\nAI RAW RESPONSE:")
    print(raw)

    selected = raw.split(" - ")[0].strip()

    print("\nAI SELECTED CODE:")
    print(selected)

    for o in options:

        if o["code"] == selected:

            print("\nMATCH FOUND:")
            print(f"{o['code']} - {o['name']}")
            print("=" * 80)

            return o["code"], o["name"]

    print("\nAI FAILED -> FALLBACK")

    print(
        f"FALLBACK SELECTED: "
        f"{options[0]['code']} - {options[0]['name']}"
    )

    print("=" * 80)

    return options[0]["code"], options[0]["name"]