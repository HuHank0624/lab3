# Lab3 - 遊戲大廳與商城平台

網路程式設計作業三：整合遊戲大廳（Lobby）與遊戲商城（Store）的平台系統。

## 📁 專案架構

```
lab3/
├── server/              # 伺服器端程式碼
│   ├── server.py        # 主伺服器入口
│   ├── auth.py          # 認證管理
│   ├── data.py          # 資料存取層 (JSON DB)
│   ├── handlers.py      # 請求處理器
│   ├── game_manager.py  # 遊戲上架管理
│   ├── game_runtime.py  # 遊戲執行環境
│   ├── lobby_manager.py # 大廳/房間管理
│   └── db/              # 資料庫檔案
├── developer_client/    # 開發者客戶端
│   ├── client.py        # 開發者客戶端入口
│   ├── menu.py          # 選單介面
│   ├── auth.py          # 認證
│   ├── game_upload.py   # 遊戲上傳
│   └── game_manage.py   # 遊戲管理
├── player_client/       # 玩家客戶端
│   ├── client.py        # 玩家客戶端入口
│   ├── menu.py          # 選單介面
│   ├── auth.py          # 認證
│   ├── store.py         # 遊戲商城
│   ├── lobby.py         # 遊戲大廳
│   ├── library.py       # 本地遊戲庫
│   └── review.py        # 評分評論
├── utils/               # 共用工具
│   ├── protocol.py      # 通訊協定
│   └── file_transfer.py # 檔案傳輸工具
└── games/               # 範例遊戲
    └── gomoku/          # 五子棋
```

## 🚀 快速開始

### 環境需求
- Python 3.10+
- 無需額外套件

### 1. 啟動伺服器

```bash
cd lab3
python -m server.server
```

預設監聽 `0.0.0.0:5555`

### 2. 啟動開發者客戶端

```bash
cd lab3
python -m developer_client.client
```

### 3. 啟動玩家客戶端

```bash
cd lab3
python -m player_client.client
```

## 📖 使用流程

### 開發者操作流程

1. **註冊/登入**
   - 選擇 `1. Register` 註冊新帳號
   - 選擇 `2. Login` 登入

2. **上架新遊戲**
   - 選擇 `1. Upload new game`
   - 輸入遊戲名稱、版本、描述
   - 輸入 Server Entry 和 Client Entry 檔案名稱
   - 輸入遊戲資料夾路徑

3. **管理遊戲**
   - `3. List my games` - 查看已上架的遊戲
   - `2. Update existing game` - 更新遊戲版本
   - `4. Delete game` - 下架遊戲

### 玩家操作流程

1. **註冊/登入**
   - 選擇 `1. 註冊帳號` 註冊新帳號
   - 選擇 `2. 登入` 登入

2. **瀏覽商城與下載遊戲**
   - 選擇 `1. 瀏覽遊戲商城`
   - 按 `v` 查看遊戲詳情
   - 按 `d` 下載遊戲

3. **進入大廳遊玩**
   - 選擇 `3. 進入遊戲大廳`
   - `1. 查看房間列表` - 查看現有房間
   - `2. 建立新房間` - 建立遊戲房間
   - `3. 加入房間` - 加入他人房間
   - `5. 開始遊戲` - 房主啟動遊戲

4. **評分與評論**
   - 選擇 `4. 對遊戲評分與留言`
   - 選擇遊戲並給予 1-5 星評分

## 🎮 遊戲規格

上架的遊戲需符合以下規格：

### 檔案結構
```
game_folder/
├── game_server.py   # 遊戲伺服器 (必須)
├── game_client.py   # 遊戲客戶端 (必須)
└── [其他檔案]       # 其他必要檔案
```

### 啟動參數
- Server: `python game_server.py --port <port>`
- Client: `python game_client.py --host <host> --port <port> --name <player_name>`

### 通訊協定
使用 4-byte length prefix + JSON 格式：
```
[4 bytes: length][JSON payload]
```

## 🔧 設定

### 修改伺服器連線資訊

**開發者客戶端** - 編輯 `developer_client/client.py`:
```python
SERVER_HOST = "127.0.0.1"  # 伺服器 IP
SERVER_PORT = 5555          # 伺服器 Port
```

**玩家客戶端** - 編輯 `player_client/client.py`:
```python
SERVER_HOST = "127.0.0.1"  # 伺服器 IP
SERVER_PORT = 5555          # 伺服器 Port
```

### 修改伺服器監聽設定

編輯 `server/utils.py`:
```python
SERVER_HOST = "0.0.0.0"    # 監聽 IP
SERVER_PORT = 5555          # 監聯 Port
```

## 📝 範例：上架五子棋遊戲

1. 啟動開發者客戶端並登入
2. 選擇上架新遊戲
3. 輸入資訊：
   - Game Name: `Gomoku`
   - Version: `1.0.0`
   - Description: `Classic Gomoku game`
   - Server Entry: `gomoku_server.py`
   - Client Entry: `gomoku_client.py`
   - Path: `games/gomoku`

## 🗄️ 資料儲存

伺服器資料儲存於 `server/db/` 目錄：
- `users.json` - 使用者帳號
- `games.json` - 遊戲資訊
- `rooms.json` - 房間資訊

上架的遊戲檔案儲存於 `server/storage/`

## ⚠️ 注意事項

1. 每位玩家的下載目錄獨立（`player_client/downloads/<username>/`）
2. 遊戲解壓後存放於 `player_client/games/<game_id>_<name>/`
3. 伺服器重啟後資料不會遺失（持久化至 JSON 檔案）
4. 同一帳號同一時間只允許一個登入 Session