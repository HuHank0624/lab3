.PHONY: server dev player reset clean deploy

# Start the server (run on linux{1,2,3,4}.cs.nycu.edu.tw)
server:
	python3 -m server.server

# Start server in background (for deployment)
server-bg:
	nohup python3 -m server.server > server.log 2>&1 &
	@echo "Server started in background. Check server.log for output."
	@echo "To stop: pkill -f 'python3 -m server.server'"

# Start developer client
dev:
	python3 -m developer_client.client

# Start player client
player:
	python3 -m player_client.client

# Reset database
reset:
	python3 reset_db.py

# Clean generated files
clean:
	rm -rf server/db/*.json
	rm -rf server/storage/runtime/*
	rm -rf player_client/downloads/*
	rm -rf player_client/games/*
	python3 reset_db.py

# Setup virtual environment
venv:
	python3 -m venv venv
	@echo "Run 'source venv/bin/activate' to activate"

# Show help
help:
	@echo "Game Platform Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make server     - Start the main server (foreground)"
	@echo "  make server-bg  - Start server in background (for deployment)"
	@echo "  make dev        - Start developer client"
	@echo "  make player     - Start player client"
	@echo "  make reset      - Reset database"
	@echo "  make clean      - Clean all generated files"
	@echo "  make venv       - Create virtual environment"
	@echo ""
	@echo "Server Deployment (on linux{1,2,3,4}.cs.nycu.edu.tw):"
	@echo "  1. ssh to school server"
	@echo "  2. git clone your repo"
	@echo "  3. make reset && make server-bg"
	@echo "  4. Server runs on port 10001"
