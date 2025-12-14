# Game Lobby & Store Platform

A Steam-like multiplayer game platform for Network Programming course (Lab 3).

## Project Structure

```
lab3/
├── server/                 # Backend Server
│   ├── server.py          # Main server entry
│   ├── handlers.py        # Request handlers
│   ├── data.py            # JSON database layer
│   ├── lobby_manager.py   # Room management
│   ├── game_manager.py    # Game uploads & ports
│   ├── game_runtime.py    # Game server launcher
│   └── db/                # Database files
│       ├── users.json
│       ├── games.json
│       └── rooms.json
│
├── developer_client/       # Developer Client
│   ├── client.py          # Entry point
│   ├── auth.py            # Registration/Login
│   ├── game_upload.py     # Upload games
│   ├── game_manage.py     # Manage uploaded games
│   ├── games/             # Local game development folder
│   │   └── gomoku/        # Example: Gomoku game
│   ├── template/          # Game templates
│   │   ├── game_server_template.py
│   │   └── game_client_template.py
│   └── create_game_template.py  # Create new game project
│
├── player_client/          # Player Client
│   ├── client.py          # Entry point
│   ├── auth.py            # Registration/Login
│   ├── store.py           # Browse & download games
│   ├── lobby.py           # Game rooms & matchmaking
│   ├── library.py         # View downloaded games
│   ├── review.py          # Rate & review games
│   ├── downloads/         # Downloaded zip files (per user)
│   └── games/             # Extracted games (per user)
│       └── <username>/    # Each player has own folder
│           └── <game_name>/
│
├── utils/                  # Shared utilities
│   ├── protocol.py        # JSON protocol (send/recv)
│   └── file_transfer.py   # Chunked file transfer
│
├── start_server.bat       # Quick start server
├── start_developer.bat    # Quick start developer client
├── start_player.bat       # Quick start player client
└── reset_db.py            # Reset database
```

## Quick Start

### 1. Start the Server
```bash
python -m server.server
# Or double-click: start_server.bat
```
Server listens on port **10001**.

### 2. Start Developer Client
```bash
python -m developer_client.client
# Or double-click: start_developer.bat
```

### 3. Start Player Client
```bash
python -m player_client.client
# Or double-click: start_player.bat
```

## Configuration

### Change Server IP/Port

Edit these files to change connection settings:

| File | Variable |
|------|----------|
| `server/utils.py` | `SERVER_PORT = 10001` |
| `player_client/client.py` | `SERVER_HOST`, `SERVER_PORT` |
| `developer_client/client.py` | `SERVER_HOST`, `SERVER_PORT` |

### Ports Used
- **10001**: Main server
- **10002+**: Game servers (auto-allocated)

## Developer Workflow

### Creating a New Game

1. Use the template generator:
   ```bash
   cd developer_client
   python create_game_template.py my_awesome_game
   ```

2. This creates:
   ```
   developer_client/games/my_awesome_game/
   ├── my_awesome_game_server.py
   ├── my_awesome_game_client.py
   └── README.md
   ```

3. Customize the game logic in the server and client files.

4. Test locally:
   ```bash
   # Terminal 1: Start server
   python my_awesome_game_server.py --port 12345
   
   # Terminal 2: Start client 1
   python my_awesome_game_client.py --host 127.0.0.1 --port 12345 --name Player1
   
   # Terminal 3: Start client 2
   python my_awesome_game_client.py --host 127.0.0.1 --port 12345 --name Player2
   ```

5. Upload via Developer Client.

### Uploading a Game

1. Start Developer Client
2. Register/Login as developer
3. Select "Upload new game"
4. Select game folder from `developer_client/games/`
5. Enter game name, description, version

## Player Workflow

### Download & Play

1. Start Player Client
2. Register/Login as player
3. Go to "Game Store" -> Browse & Download games
4. Go to "Game Lobby" -> Create or Join room
5. Host: "Start game" launches server + client
6. Guest: "Launch game client" after host starts
7. After game: Host closes room

### Per-Player Game Storage

Each player has their own game folder:
```
player_client/games/<username>/<game_name>/
```

This simulates different players on different computers, allowing:
- Different players to have different game versions
- Testing version update scenarios

## Key Features

### Room Restrictions
- Each player can only host **one room at a time**
- Must close existing room before creating new one

### Version Updates
- When developer uploads new version, old version is replaced
- Players can re-download to get latest version
- Downloaded games show version in `game_info.json`

## Database Reset

To reset all data:
```bash
python reset_db.py
```

Then restart the server.

## Demo Checklist

1. [ ] Server running on Linux machine
2. [ ] Developer registers, uploads Gomoku game
3. [ ] Player 1 registers, downloads game, creates room
4. [ ] Player 2 registers, downloads game, joins room
5. [ ] Player 1 (host) starts game
6. [ ] Player 2 launches game client
7. [ ] Both players play the game
8. [ ] After game, host closes room
9. [ ] Players can rate/review the game

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Make sure server is running |
| "You already have a room" | Close existing room first |
| Game not launching | Make sure game is downloaded |
| Room stuck in "playing" | Host should close room |
| Port already in use | Restart server or change port |

## Dependencies

- Python 3.10+
- No external dependencies (stdlib only)
