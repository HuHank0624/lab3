# reset_db.py - Reset all database JSON files to empty state
import json
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "server", "db")

def reset_db():
    # Empty users
    users_path = os.path.join(DB_DIR, "users.json")
    with open(users_path, "w", encoding="utf-8") as f:
        json.dump({"users": []}, f, indent=2)
    print(f"Reset {users_path}")

    # Empty games
    games_path = os.path.join(DB_DIR, "games.json")
    with open(games_path, "w", encoding="utf-8") as f:
        json.dump({"games": []}, f, indent=2)
    print(f"Reset {games_path}")

    # Empty rooms
    rooms_path = os.path.join(DB_DIR, "rooms.json")
    with open(rooms_path, "w", encoding="utf-8") as f:
        json.dump({"rooms": []}, f, indent=2)
    print(f"Reset {rooms_path}")

    print("\nDatabase reset complete!")
    print("NOTE: Restart the server for changes to take effect.")

if __name__ == "__main__":
    reset_db()
