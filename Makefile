# path: Makefile

PYTHON = python3

SERVER_DIR = server
DEV_DIR    = developer_client
PLAYER_DIR = player_client

# ============================
# 基本：啟動 Server / Client
# ============================

server:
	@echo "=== Starting Lobby / Store Server ==="
	$(PYTHON) $(SERVER_DIR)/server.py

dev:
	@echo "=== Starting Developer Client ==="
	$(PYTHON) $(DEV_DIR)/client.py

player:
	@echo "=== Starting Player Client ==="
	$(PYTHON) $(PLAYER_DIR)/client.py

# 可以開兩個 player 給 demo 用（其實一樣，只是方便助教記）
player1:
	@echo "=== Starting Player Client #1 ==="
	$(PYTHON) $(PLAYER_DIR)/client.py

player2:
	@echo "=== Starting Player Client #2 ==="
	$(PYTHON) $(PLAYER_DIR)/client.py

# ============================
# 快速提示 Demo 流程
# ============================

demo:
	@echo "=== HW3 Platform Demo Guide ==="
	@echo "1. 在一個 terminal 執行:  make server"
	@echo "2. 在第二個 terminal 執行: make dev"
	@echo "   - 使用 Developer 帳號登入 / 註冊"
	@echo "   - 上架一款遊戲 (例如: gomoku.zip)"
	@echo "3. 在第三、第四個 terminal 分別執行: make player1 / make player2"
	@echo "   - 使用不同 Player 帳號登入"
	@echo "   - 進入商城下載遊戲"
	@echo "   - 建立房間 / 加入房間 / start_game"
	@echo ""
	@echo "⚠ 各遊戲實際的 game server / game client"
	@echo "  應由平台內部 (server 端) 的 start_game 流程用 subprocess 啟動"
	@echo "  Makefile 不會直接啟動任一特定遊戲，也不會綁定 port。"

clean:
	find . -name "__pycache__" -exec rm -rf {} +
