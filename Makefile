.PHONY: server dev player reset clean

# Start the server
server:
	python3 -m server.server

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
	@echo "  make server   - Start the main server"
	@echo "  make dev      - Start developer client"
	@echo "  make player   - Start player client"
	@echo "  make reset    - Reset database"
	@echo "  make clean    - Clean all generated files"
	@echo "  make venv     - Create virtual environment"
