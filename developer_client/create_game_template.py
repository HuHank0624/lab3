#!/usr/bin/env python3
"""
Create Game Template
====================
This script creates a new game project from templates.
It generates the basic structure needed to develop a multiplayer game
compatible with this platform.

Usage: python create_game_template.py <game_name>
"""

import os
import sys
import re
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "template"
GAMES_DIR = Path(__file__).parent / "games"


def to_class_name(name: str) -> str:
    """Convert game_name to ClassName format."""
    return ''.join(word.capitalize() for word in re.split(r'[_\s-]', name))


def create_game_project(game_name: str):
    """Create a new game project from templates."""
    
    # Sanitize game name
    safe_name = game_name.lower().replace(' ', '_').replace('-', '_')
    class_name = to_class_name(game_name)
    
    # Create game directory
    game_dir = GAMES_DIR / safe_name
    if game_dir.exists():
        print(f"Error: Game '{safe_name}' already exists at {game_dir}")
        return False
    
    game_dir.mkdir(parents=True)
    print(f"Created game directory: {game_dir}")
    
    # Read templates
    server_template = TEMPLATE_DIR / "game_server_template.py"
    client_template = TEMPLATE_DIR / "game_client_template.py"
    
    if not server_template.exists() or not client_template.exists():
        print("Error: Template files not found. Please ensure template folder exists.")
        return False
    
    # Create server file
    server_content = server_template.read_text(encoding="utf-8")
    server_content = server_content.replace("{game_name}", safe_name)
    server_content = server_content.replace("GameLogic", f"{class_name}Logic")
    server_content = server_content.replace("GameServer", f"{class_name}Server")
    
    server_file = game_dir / f"{safe_name}_server.py"
    server_file.write_text(server_content, encoding="utf-8")
    print(f"Created: {server_file}")
    
    # Create client file
    client_content = client_template.read_text(encoding="utf-8")
    client_content = client_content.replace("{game_name}", safe_name)
    client_content = client_content.replace("GameClient", f"{class_name}Client")
    
    client_file = game_dir / f"{safe_name}_client.py"
    client_file.write_text(client_content, encoding="utf-8")
    print(f"Created: {client_file}")
    
    # Create README
    readme_content = f"""# {game_name}

## Description
A multiplayer game for the Game Platform.

## Files
- `{safe_name}_server.py` - Game server
- `{safe_name}_client.py` - Game client

## Development

### Testing locally
1. Start the server:
   ```
   python {safe_name}_server.py --port 12345
   ```

2. Start client(s) in separate terminals:
   ```
   python {safe_name}_client.py --host 127.0.0.1 --port 12345 --name Player1
   ```

### Customization
1. Edit `{class_name}Logic` class in `{safe_name}_server.py`:
   - `initialize_game()`: Set up initial game state
   - `process_move()`: Handle player moves and game logic
   - `get_state()`: Return current state to broadcast

2. Edit `{class_name}Client` class in `{safe_name}_client.py`:
   - `display_game()`: Render the game state
   - `parse_input()`: Parse player input into move data

## Uploading to Platform
Use the Developer Client to upload this game:
1. Run `python -m developer_client.client`
2. Login as developer
3. Select "Upload new game"
4. Select this game folder
"""
    
    readme_file = game_dir / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")
    print(f"Created: {readme_file}")
    
    print(f"\nGame project '{game_name}' created successfully!")
    print(f"\nNext steps:")
    print(f"1. Edit the game logic in {safe_name}_server.py")
    print(f"2. Edit the client display in {safe_name}_client.py")
    print(f"3. Test locally with --port and --host arguments")
    print(f"4. Upload via Developer Client when ready")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python create_game_template.py <game_name>")
        print("\nExamples:")
        print("  python create_game_template.py tic_tac_toe")
        print("  python create_game_template.py my_card_game")
        return
    
    game_name = " ".join(sys.argv[1:])
    
    # Ensure games directory exists
    GAMES_DIR.mkdir(exist_ok=True)
    
    create_game_project(game_name)


if __name__ == "__main__":
    main()
