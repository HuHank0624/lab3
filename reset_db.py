# reset_db.py - Reset all database JSON files and downloaded games
import json
import os
import shutil

BASE_DIR = os.path.dirname(__file__)
DB_DIR = os.path.join(BASE_DIR, "server", "db")
STORAGE_DIR = os.path.join(BASE_DIR, "server", "storage")
PLAYER_DOWNLOADS = os.path.join(BASE_DIR, "player_client", "downloads")
PLAYER_GAMES = os.path.join(BASE_DIR, "player_client", "games")


def reset_db():
    # Empty users
    users_path = os.path.join(DB_DIR, "users.json")
    with open(users_path, "w", encoding="utf-8") as f:
        json.dump({"users": []}, f, indent=2)
    print(f"[OK] Reset {users_path}")

    # Empty games
    games_path = os.path.join(DB_DIR, "games.json")
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump({"games": []}, f, indent=2)
    print(f"[OK] Reset {games_path}")

    # Empty rooms
    rooms_path = os.path.join(DB_DIR, "rooms.json")
    with open(rooms_path, "w", encoding="utf-8") as f:
        json.dump({"rooms": []}, f, indent=2)
    print(f"[OK] Reset {rooms_path}")

    # Clear server storage (uploaded game files)
    if os.path.exists(STORAGE_DIR):
        for item in os.listdir(STORAGE_DIR):
            item_path = os.path.join(STORAGE_DIR, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"[OK] Removed server storage: {item}")
    print(f"[OK] Cleared {STORAGE_DIR}")

    # Clear player downloaded zip files
    if os.path.exists(PLAYER_DOWNLOADS):
        for item in os.listdir(PLAYER_DOWNLOADS):
            item_path = os.path.join(PLAYER_DOWNLOADS, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        print(f"[OK] Cleared {PLAYER_DOWNLOADS}")

    # Clear player extracted games
    if os.path.exists(PLAYER_GAMES):
        for item in os.listdir(PLAYER_GAMES):
            item_path = os.path.join(PLAYER_GAMES, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        print(f"[OK] Cleared {PLAYER_GAMES}")

    print("\n=== Reset Complete ===")
    print("- Server database cleared")
    print("- Server game storage cleared")
    print("- Player downloads cleared")
    print("- Player games cleared")
    print("\nNOTE: Restart the server for changes to take effect.")


if __name__ == "__main__":
    reset_db()
