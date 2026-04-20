.PHONY: install install-browsers search ui test lint typecheck format clean

install:
	pip install -e ".[dev]"

install-browsers:
	playwright install chromium

search:
	python scripts/search.py --interactive

ui:
	streamlit run app/main.py

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	mypy src/

format:
	ruff format src/ tests/

clean:
	rm -rf data/*.db .pytest_cache .ruff_cache .mypy_cache __pycache__
