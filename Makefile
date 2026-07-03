# Gaurav Singh Thakur — MIT License
#
# Common dev commands. Run `make help` to see the list.

.PHONY: help install seed run test docker-up docker-down clean

help:
	@echo ""
	@echo "VendorVault — available commands:"
	@echo ""
	@echo "  make install     Install Python dependencies"
	@echo "  make seed        Seed the database with starting data"
	@echo "  make run         Start the dev server on http://localhost:5000"
	@echo "  make test        Run the test suite"
	@echo "  make setup       Full first-time setup: install + seed + run"
	@echo "  make docker-up   Start with Docker Compose"
	@echo "  make docker-down Stop Docker Compose"
	@echo "  make clean       Delete the local database (start fresh)"
	@echo ""

install:
	pip install -r requirements.txt

seed:
	python seed.py

run:
	python app.py

test:
	python -m pytest tests/ -v

setup: install seed run

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	@echo "Deleting local database..."
	rm -f vendorvault.db vendorvault.db-wal vendorvault.db-shm
	@echo "Done. Run 'make seed' to start fresh."
