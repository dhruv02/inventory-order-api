# Inventory & Order Management API

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)

A portfolio-ready **Python FastAPI + SQLAlchemy + SQLite** REST API implementing inventory control and sales ordering. Inspired by real-world stock management workflows.

## Features

- Create and search inventory products with unique SKUs, prices, quantity on hand and reorder thresholds.
- Adjust stock with input validation and insufficient-stock safeguards.
- Filter products that need replenishment.
- Create orders containing multiple products and automatically deduct inventory.
- Validate **every order line before committing** to avoid partial fulfillment on routine errors.
- Persist orders and line-item price snapshots in a relational database.
- Inspect aggregate inventory metrics and interactive OpenAPI documentation.
- Run automated API tests using **pytest, HTTPX, in-memory SQLite**, and code coverage checks.
- Use **GitHub Actions CI** to lint and test the project on Python 3.11, 3.12 and 3.13.

## Tech stack

Python · FastAPI · Pydantic v2 · SQLAlchemy 2 · SQLite · pytest · HTTPX · pytest-cov · Ruff · GitHub Actions

## VS Code / local setup

1. Install Python 3.11+ and open this folder in VS Code.
2. Open VS Code Terminal and create a virtual environment:
   - Windows PowerShell: `py -m venv .venv` then `.venv\\Scripts\\Activate.ps1`
   - macOS / Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. Install the package and development dependencies:

   ```bash
   python -m pip install -e ".[dev]"
   ```

4. Start the server:

   ```bash
   uvicorn inventory_api.main:app --reload
   ```

5. Open <http://127.0.0.1:8000/docs> for interactive Swagger UI.

The database file is created automatically on application startup. The service is intentionally unauthenticated for **local demonstration only**—do not expose it to the public internet without authentication, authorization, and other production safeguards.

## Try a product and an order

Create a product:

```bash
curl -X POST http://127.0.0.1:8000/products \
  -H 'Content-Type: application/json' \
  -d '{"sku":"APL001","name":"Apples","price":"2.50","stock":20,"reorder_level":5}'
```

Create an order using the returned product ID (shown as 1 below):

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"product_id":1,"quantity":3}]}'
```

View inventory metrics:

```bash
curl http://127.0.0.1:8000/metrics/inventory
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Service health |
| POST | `/products` | Add a product |
| GET | `/products` | Search and filter products |
| GET | `/products/{product_id}` | Get one product |
| PATCH | `/products/{product_id}/stock` | Restock or reduce inventory |
| POST | `/orders` | Place order and deduct stock |
| GET | `/orders/{order_id}` | Read an order receipt |
| GET | `/metrics/inventory` | Stock and order metrics |

## Run quality checks

```bash
ruff check .
pytest
```

The GitHub Actions workflow executes the same checks automatically on pushes and pull requests. The test suite uses a fresh in-memory test database per test; no real database or credentials are required.

## Architecture

```
src/inventory_api/
  main.py       # API endpoints and order workflow
  schemas.py    # Pydantic input validation and response contracts
  models.py     # SQLAlchemy tables and relations
  database.py   # Database engine and session dependency
tests/
  conftest.py   # Isolated in-memory test database
  test_api.py   # API and business-rule regression tests
.github/workflows/ci.yml
```

## Future improvements

- Authentication and per-user permissions.
- Database migrations with Alembic and PostgreSQL integration.
- Optimistic locking or database-level row locks to prevent concurrent overselling.
- Pagination, rate limiting, structured logging, and production deployment.
- Web dashboard and additional reporting.

**Scope note:** Transactional validation protects routine single-request failures but is not a guarantee against concurrent orders on SQLite. For real inventory systems, implement appropriate database concurrency controls.

## Resume project description (once published and independently verified)

**Inventory & Order Management API** — Python, FastAPI, SQLAlchemy, SQLite, pytest, GitHub Actions
- Developed an inventory and order management REST API with input validation, relational data models, stock adjustments, low-stock alerts, and order processing.
- Built automated API tests covering CRUD workflows, validation, insufficient inventory, and multi-item orders using pytest and an isolated SQLite test database.
- Configured GitHub Actions CI to lint the code and execute tests across multiple Python versions.

No public deployment or production-scale performance claim is implied.
