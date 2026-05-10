"""Tests for app.services.clod_service — HTTP mocked."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("CLOD_API_KEY", "test-clod-key")

from app.services.clod_service import ClodService


def _make_response(content: str, model: str = "clod-unified-smart", status: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "model": model,
    }
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = json.dumps(mock_resp.json())
    return mock_resp


class TestClodServiceEvaluateAndGenerate:
    @pytest.mark.asyncio
    async def test_returns_tuple(self):
        resp = _make_response("def foo(): pass")
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
            result = await ClodService.evaluate_and_generate("Build a thing", [])
        assert isinstance(result, tuple) and len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_generated_code(self):
        resp = _make_response("def wallet(): return True")
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
            _, code = await ClodService.evaluate_and_generate("Wallet", [])
        assert "def wallet" in code

    @pytest.mark.asyncio
    async def test_http_error_returns_mock_fallback(self):
        import httpx
        err_resp = MagicMock()
        err_resp.status_code = 500
        err_resp.text = "err"
        with patch(
            "httpx.AsyncClient.post",
            new=AsyncMock(side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=err_resp)),
        ):
            model, _ = await ClodService.evaluate_and_generate("task", [])
        assert model == "mocked-claude-3-haiku"

    @pytest.mark.asyncio
    async def test_network_error_returns_mock_fallback(self):
        with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=Exception("conn refused"))):
            model, _ = await ClodService.evaluate_and_generate("task", [])
        assert model == "mocked-claude-3-haiku"

    @pytest.mark.asyncio
    async def test_empty_constraints_does_not_crash(self):
        resp = _make_response("result code")
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=resp)):
            _, code = await ClodService.evaluate_and_generate("task", [])
        assert code == "result code"
