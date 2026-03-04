#!/usr/bin/env bash
set -euo pipefail

COMMAND=${1:-help}

case "$COMMAND" in
  install)
    echo "==> Installing dependencies..."
    pip install uv 2>/dev/null || true
    uv pip install --system ".[dev]" || pip install ".[dev]"
    echo "==> Done!"
    ;;
  lint)
    echo "==> Running linter..."
    ruff check app/ tests/
    ruff format --check app/ tests/
    echo "==> Lint passed!"
    ;;
  format)
    echo "==> Formatting code..."
    ruff format app/ tests/
    ruff check --fix app/ tests/
    echo "==> Done!"
    ;;
  test)
    echo "==> Running tests..."
    pytest tests/ -v --cov=app --cov-report=term-missing
    ;;
  test-unit)
    echo "==> Running unit tests..."
    pytest tests/unit/ -v
    ;;
  test-e2e)
    echo "==> Running E2E tests..."
    pytest tests/e2e/ -v
    ;;
  build)
    echo "==> Building Docker images..."
    docker compose build
    echo "==> Done!"
    ;;
  run)
    echo "==> Starting services..."
    docker compose up -d
    echo ""
    echo "  API:       http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo "  MongoDB:   mongodb://localhost:27017"
    echo ""
    ;;
  run-debug)
    echo "==> Starting services with debug tools..."
    docker compose --profile debug up -d
    echo ""
    echo "  API:           http://localhost:8000"
    echo "  API Docs:      http://localhost:8000/docs"
    echo "  Mongo Express: http://localhost:8081"
    echo ""
    ;;
  stop)
    echo "==> Stopping services..."
    docker compose --profile debug down
    echo "==> Done!"
    ;;
  clean)
    echo "==> Cleaning up..."
    docker compose --profile debug down -v
    echo "==> Done!"
    ;;
  all)
    $0 install && $0 lint && $0 test && $0 build
    ;;
  help|*)
    echo "Squad Nous Build Script"
    echo ""
    echo "Usage: ./build.sh <command>"
    echo ""
    echo "Commands:"
    echo "  install     Install Python dependencies"
    echo "  lint        Run linter (ruff)"
    echo "  format      Format code (ruff)"
    echo "  test        Run all tests with coverage"
    echo "  test-unit   Run unit tests only"
    echo "  test-e2e    Run E2E tests only"
    echo "  build       Build Docker images"
    echo "  run         Start services (API + MongoDB)"
    echo "  run-debug   Start services with Mongo Express"
    echo "  stop        Stop all services"
    echo "  clean       Stop services and remove volumes"
    echo "  all         Install, lint, test, and build"
    ;;
esac
