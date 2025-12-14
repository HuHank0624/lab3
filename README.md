# Game Lobby & Store Platform

A multiplayer game platform with lobby, store, developer upload, and game runtime support.

---

## 📋 Requirements Checklist

### Account System ✅
- [x] Developer and Player accounts are **separate** (different registration)
- [x] Simple username + password registration
- [x] No duplicate usernames (checked during registration)
- [x] Login validation (password check)
- [x] One session per account (new login overwrites old session)

### Developer Platform ✅
- [x] **D1: Upload new game** - Developers can upload games with name, version, description
- [x] **D2: Update game** - Re-upload with new version number
- [x] **D3: Delete/Unlist game** - Remove game from store
- [x] Developer can only manage their own games
- [x] Game template system (`create_game_template.py`)
- [x] Developer games stored in `developer_client/games/`

### Player Platform ✅
- [x] **P1: Browse store** - View game list, details, ratings, reviews
- [x] **P2: Download games** - Download to per-user folder (`player_client/games/<username>/`)
- [x] **P3: Create room & Start game** - Host-only start, auto-launch game server
- [x] **P4: Rate & Review** - 1-5 star rating with comments
- [x] Per-user game folders (simulates multiple players on same machine)
- [x] One room per player limit

### Server Features ✅
- [x] Data persists after restart (JSON files in `server/db/`)
- [x] Game file storage (`server/storage/uploads/`)
- [x] Game runtime extraction (`server/storage/runtime/`)
- [x] Room management (create, join, leave, close)
- [x] Game server auto-launch

### Menu-Driven Interface ✅
- [x] Clear numbered options at each step
- [x] Pagination for long menus (max 5 options per page)
- [x] No command-line knowledge required

---

## 🚀 Quick Start (Local Testing)

### 1. Start Server
```bash
# Terminal 1: Server
make reset  # Reset database (optional, for clean start)
make server
```

### 2. Start Developer Client (Upload a Game)
```bash
# Terminal 2: Developer
make dev
```

### 3. Start Player Clients (Multiple Players)
```bash
# Terminal 3: Player 1
make player

# Terminal 4: Player 2 (separate terminal)
make player
```

---

## 🧪 Complete Test Routine

### Phase 1: Developer Workflow

#### 1.1 Developer Registration & Login
```
Developer Menu:
1. Register → username: dev1, password: 123
2. Login → dev1 / 123
```

#### 1.2 Upload Game (Use Case D1)
```
Developer Dashboard:
1. Upload new game
   - Select from available games (e.g., gomoku)
   - Fill in:
     * Game Name: Gomoku
     * Version: 1.0.0
     * Description: Two-player Gomoku game
     * Server Entry: gomoku_server.py
     * Client Entry: gomoku_client.py
   - Confirm upload
```

#### 1.3 Verify Upload
```
Developer Dashboard:
3. List my games → Should see "Gomoku" with download count 0
```

#### 1.4 Update Game (Use Case D2)
```
Developer Dashboard:
2. Update existing game
   - Select game
   - Re-upload with Version: 1.0.1
```

---

### Phase 2: Player 1 Workflow

#### 2.1 Player 1 Registration & Login
```
Player Menu:
1. Register → username: player1, password: 123
2. Login → player1 / 123
```

#### 2.2 Browse Store (Use Case P1)
```
Player Menu (Logged In):
1. Browse Game Store
   - See list of games with ratings
   v. View game details
   - Select game → See description, reviews, developer info
```

#### 2.3 Download Game (Use Case P2)
```
Game Store:
d. Download game
   - Select game number
   - Wait for download complete
   - Game extracted to: player_client/games/player1/Gomoku/
```

#### 2.4 Check Library
```
Player Menu:
2. My Game Library
   - Should see downloaded games
```

#### 2.5 Create Room (Use Case P3)
```
Player Menu:
3. Enter Game Lobby
   1. View room list → (empty initially)
   2. Create new room
      - Select game (Gomoku)
      - Room name: "Player1's Room"
      - Max players: 2
   → Room created! Note the Room ID and Port
```

---

### Phase 3: Player 2 Workflow

#### 3.1 Player 2 Setup (New Terminal)
```
Player Menu:
1. Register → username: player2, password: 123
2. Login → player2 / 123
```

#### 3.2 Download Same Game
```
Browse Game Store → Download Gomoku
→ Extracted to: player_client/games/player2/Gomoku/
```

#### 3.3 Join Room
```
Enter Game Lobby:
1. View room list → See "Player1's Room"
3. Join room → Enter room_id
```

---

### Phase 4: Game Play

#### 4.1 Host (Player 1) Starts Game
```
Game Lobby (page 2):
5. Start game (host only)
   → Game starting on port XXXXX
   → Game server launched
   → Game client launched for host
```

#### 4.2 Guest (Player 2) Joins Game
```
Game Lobby (page 2):
6. Launch game client
   → Game client connects to running server
```

#### 4.3 Play the Game
- Both players should now be in the game
- Play until game ends

#### 4.4 Close Room (Host)
```
Game Lobby (page 2):
7. Close room (host only)
   → Room deleted, game server stopped
```

---

### Phase 5: Review System (Use Case P4)

#### 5.1 Rate & Review
```
Player Menu:
4. Rate & Review Games
   - Select game
   - Enter rating: 5
   - Enter comment: "Great game!"
```

#### 5.2 Verify Review
```
Browse Game Store:
v. View game details
   → Should show average rating and reviews
```

---

### Phase 6: Developer Delete Game (Use Case D3)

```
Developer Dashboard:
4. Delete (unlist) game
   - Select game
   - Type "DELETE" to confirm
   → Game removed from store
```

---

## ⚠️ Error Scenarios to Test

### Account Errors
1. **Duplicate Registration**: Register with existing username → "Username already exists"
2. **Wrong Password**: Login with wrong password → "Invalid credentials"
3. **Not Logged In**: Try to create room without login → "Not logged in"

### Game Management Errors
1. **Download Non-Existent Game**: Game deleted while downloading → "Game not found"
2. **Create Room Without Download**: Try to create room for undownloaded game → "Please download first"
3. **Start Game as Non-Host**: Non-host tries to start → "Only the host can start"
4. **Double Room Creation**: Try to create second room → "You already have a room"

### Network Errors
1. **Server Down**: Start client without server → "Connection refused"

---

## 📁 Project Structure

```
lab3/
├── config.py                 # Server host/port configuration
├── Makefile                  # Build/run commands
├── server/
│   ├── server.py            # Main server entry
│   ├── handlers.py          # Request dispatcher
│   ├── auth.py              # Authentication manager
│   ├── data.py              # JSON database layer
│   ├── game_manager.py      # Game upload/download
│   ├── lobby_manager.py     # Room management
│   ├── game_runtime.py      # Game server launcher
│   ├── db/
│   │   ├── users.json       # User accounts
│   │   ├── games.json       # Game metadata
│   │   └── rooms.json       # Active rooms
│   └── storage/
│       ├── uploads/         # Uploaded game ZIPs
│       └── runtime/         # Extracted games for server
│
├── developer_client/
│   ├── client.py            # Developer client entry
│   ├── menu.py              # Developer menus
│   ├── auth.py              # Developer authentication
│   ├── game_upload.py       # Game upload logic
│   ├── game_manage.py       # Update/delete games
│   ├── games/               # Developer's local games
│   │   └── gomoku/          # Example game
│   ├── template/            # Game templates
│   └── create_game_template.py
│
├── player_client/
│   ├── client.py            # Player client entry
│   ├── menu.py              # Player menus
│   ├── auth.py              # Player authentication
│   ├── store.py             # Browse & download games
│   ├── lobby.py             # Room management & game launch
│   ├── library.py           # Local game library
│   ├── review.py            # Rating & reviews
│   ├── downloads/           # Downloaded ZIPs (per user)
│   └── games/               # Extracted games (per user)
│       ├── player1/
│       │   └── Gomoku/
│       └── player2/
│           └── Gomoku/
│
└── utils/
    ├── protocol.py          # JSON protocol helpers
    └── file_transfer.py     # Chunked file transfer
```

---

## 🔧 Configuration

Edit `config.py` to change server address:

```python
# For local testing:
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 10001

# For school server deployment:
# SERVER_HOST = "linux1.cs.nycu.edu.tw"
# SERVER_PORT = 10001
```

---

## 🖥️ School Server Deployment

### On School Server (SSH)
```bash
ssh user@linux1.cs.nycu.edu.tw
cd lab3
make reset          # Clean start
make server-bg      # Run server in background
```

### On TA's Machine
```bash
# Edit config.py:
SERVER_HOST = "linux1.cs.nycu.edu.tw"

make dev    # Developer client
make player # Player client
```

### Stop Server
```bash
pkill -f 'python3 -m server.server'
```

---

## 📝 Notes

### Per-User Folders
Each player has separate download/game folders:
- `player_client/downloads/<username>/` - Downloaded ZIPs
- `player_client/games/<username>/` - Extracted games

This simulates multiple players on different machines during demo.

### Game Template
Create new games using the template system:
```bash
cd developer_client
python create_game_template.py my_new_game
```

This creates `developer_client/games/my_new_game/` with:
- `my_new_game_server.py`
- `my_new_game_client.py`

### Version Management
- Games are identified by `game_id`
- Re-uploading updates the version
- Players can re-download to get the latest version
