# Game Lobby & Store Platform

A multiplayer game platform with lobby, store, developer upload, and game runtime support.

---

## How to Run

### 1. Start Server (on remote machine)
```bash
# SSH to school server
ssh <host_name>@linux1.cs.nycu.edu.tw

# Navigate to project directory
cd lab3

# Reset database (optional, for clean start)
python3 reset_db.py

# Start server
python3 -m server.server

# Or run in background
nohup python3 -m server.server > server.log 2>&1 &
```

### 2. Configure Client
Edit `config.py` on your local machine:
```python
SERVER_HOST = "linux1.cs.nycu.edu.tw"
SERVER_PORT = 10167  # Use your assigned port
```

### 3. Start Developer Client
```bash
python -m developer_client.client
```

### 4. Start Player Client
```bash
python -m player_client.client
```

---

## Menu Options

### Developer Client

#### Main Menu (Not Logged In)
| Option | Description |
|--------|-------------|
| 1. Register | Create a new developer account |
| 2. Login | Login to existing developer account |
| 0. Exit | Exit the client |

#### Developer Dashboard (Logged In)
| Option | Description |
|--------|-------------|
| 1. Upload new game | Upload a new game to the store |
| 2. Update existing game | Update an uploaded game (new version) |
| 3. List my games | View all your uploaded games |
| 4. Delete (unlist) game | Remove a game from the store |
| 0. Logout | Logout and return to main menu |

---

### Player Client

#### Main Menu (Not Logged In)
| Option | Description |
|--------|-------------|
| 1. Register | Create a new player account |
| 2. Login | Login to existing player account |
| 0. Exit | Exit the client |

#### Player Dashboard (Logged In)
| Option | Description |
|--------|-------------|
| 1. Browse Game Store | View and download available games |
| 2. My Game Library | View downloaded games |
| 3. Enter Game Lobby | Create or join game rooms |
| 4. Rate & Review Games | Rate and review downloaded games |
| 0. Logout | Logout and return to main menu |

#### Game Store Options
| Option | Description |
|--------|-------------|
| v | View game details (description, reviews) |
| d | Download a game |
| 0 | Back to dashboard |

#### Game Lobby Options
| Option | Description |
|--------|-------------|
| 1 | View room list |
| 2 | Create new room |
| 3 | Join room |
| 0 | Back to dashboard |

#### Waiting Room Options (After joining/creating a room)
| Option | Description |
|--------|-------------|
| r | Toggle ready status |
| s | Start game (host only, requires all players ready) |
| q | Leave room / Close room (host) |
| Enter | Refresh room status |

---

## Implementation Details

### Server Side (`server/`)

| File | What it implements |
|------|-------------------|
| `server.py` | Main TCP server using `socket` and `threading`. Accepts client connections, spawns a thread per client. |
| `handlers.py` | Request dispatcher - routes JSON actions (`register`, `login`, `upload_game`, `create_room`, etc.) to appropriate handlers. |
| `auth.py` | User authentication - password hashing with `hashlib`, session token generation, login/register logic. |
| `data.py` | JSON file database layer - CRUD operations for `users.json`, `games.json`, `rooms.json` with file locking. |
| `game_manager.py` | Game upload/download - receives chunked file uploads, stores ZIPs, manages game metadata. |
| `lobby_manager.py` | Room management - create/join/leave rooms, ready status, player tracking. |
| `game_runtime.py` | Game server launcher - extracts game files, spawns game server subprocess on assigned port. |

### Developer Client (`developer_client/`)

| File | What it implements |
|------|-------------------|
| `client.py` | Entry point - establishes socket connection to server, starts menu loop. |
| `menu.py` | Developer menu UI - displays options, handles user input, calls appropriate functions. |
| `auth.py` | Developer authentication - sends `register`/`login` requests to server, stores session token. |
| `game_upload.py` | Game upload - ZIPs local game folder, sends via chunked file transfer protocol. |
| `game_manage.py` | Game management - list uploaded games, update game version, delete (unlist) games. |

### Player Client (`player_client/`)

| File | What it implements |
|------|-------------------|
| `client.py` | Entry point - establishes socket connection to server, starts menu loop. |
| `menu.py` | Player menu UI - displays options, handles user input, calls appropriate functions. |
| `auth.py` | Player authentication - sends `register`/`login` requests to server, stores session token. |
| `store.py` | Game store - browse games, view details, download games via chunked file transfer. |
| `library.py` | Local game library - lists downloaded games from `games/<username>/` folder. |
| `lobby.py` | Game lobby - create/join rooms, waiting room with ready system, auto-launch game client. |
| `review.py` | Review system - submit ratings (1-5) and comments for downloaded games. |

### Utils (`utils/`)

| File | What it implements |
|------|-------------------|
| `protocol.py` | JSON protocol - 4-byte length-prefixed message format, `send_json()` and `recv_json()` functions. |
| `file_transfer.py` | Chunked file transfer - sends/receives large files in chunks with progress tracking. |

### Games (`developer_client/games/`)

| Game | Server | Client | Description |
|------|--------|--------|-------------|
| Gomoku | `gomoku_server.py` | `gomoku_client_gui.py` | 15x15 board, 2 players take turns, first to 5-in-a-row wins. Uses Tkinter GUI. |
| Tetris | `tetris_server.py` | `tetris_client_gui.py` | 2-player competitive Tetris, clearing lines sends garbage to opponent. Uses Tkinter GUI. |
| Swing | `swing_server.py` | `swing_client_gui.py` | 2-8 players press left/right arrows rapidly, highest swing count after 10 seconds wins. Uses Tkinter GUI. |

---

## Project Structure

```
lab3/
├── config.py                 # Server host/port configuration
├── server/
│   ├── server.py            # Main server entry
│   ├── handlers.py          # Request dispatcher
│   ├── auth.py              # Authentication manager
│   ├── data.py              # JSON database layer
│   ├── game_manager.py      # Game upload/download
│   ├── lobby_manager.py     # Room management
│   └── game_runtime.py      # Game server launcher
│
├── developer_client/
│   ├── client.py            # Developer client entry
│   ├── menu.py              # Developer menus
│   ├── auth.py              # Developer authentication
│   ├── game_upload.py       # Game upload logic
│   ├── game_manage.py       # Update/delete games
│   └── games/               # Developer's local games
│
├── player_client/
│   ├── client.py            # Player client entry
│   ├── menu.py              # Player menus
│   ├── auth.py              # Player authentication
│   ├── store.py             # Browse & download games
│   ├── lobby.py             # Room management & game launch
│   ├── library.py           # Local game library
│   └── review.py            # Rating & reviews
│
└── utils/
    ├── protocol.py          # JSON protocol helpers
    └── file_transfer.py     # Chunked file transfer
```

---

## Configuration

Edit `config.py`:
```python
SERVER_HOST = "linux1.cs.nycu.edu.tw"
SERVER_PORT = 10167
```

---

## Available Games

| Game | Description | Players |
|------|-------------|---------|
| Gomoku | Classic 5-in-a-row board game | 2 |
| Tetris | Competitive Tetris battle | 2 |
| Swing | Swing sword left/right competition | 2-8 |

---

## Server Management

| Task | Command |
|------|---------|
| Start Server (foreground) | `python3 -m server.server` |
| Start Server (background) | `nohup python3 -m server.server > server.log 2>&1 &` |
| Check if running | `ps aux \| grep server` |
| View live logs | `tail -f server.log` |
| Stop Server | `pkill -f 'python3 -m server.server'` |
| Check port | `ss -tlnp \| grep 10167` |
| Reset database | `python3 reset_db.py` |
