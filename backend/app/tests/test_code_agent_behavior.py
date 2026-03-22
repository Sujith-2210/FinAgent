import pytest
from unittest.mock import AsyncMock

from app.agents.code import CodeAgent
from app.core.cache import cache_manager


class DummySandbox:
    def __init__(self, exec_result):
        self.exec_result = exec_result
        self.calls = 0

    def execute_code(self, _code: str):
        self.calls += 1
        return self.exec_result


class SequenceSandbox:
    def __init__(self, exec_results):
        self.exec_results = list(exec_results)
        self.calls = 0

    def execute_code(self, _code: str):
        self.calls += 1
        if self.exec_results:
            return self.exec_results.pop(0)
        return {"success": False, "stdout": "", "stderr": "No more queued results", "images": []}


@pytest.mark.asyncio
async def test_prediction_ignores_stale_cached_result_without_images(monkeypatch):
    stale_cached = {
        "success": True,
        "images": [],
        "output": "stale",
        "explanation": "stale cached response",
    }
    fresh_exec = {
        "success": True,
        "stdout": "fresh run",
        "stderr": "",
        "images": [{"name": "plot_1.png", "base64": "abc"}],
    }

    sandbox = DummySandbox(fresh_exec)
    agent = CodeAgent(sandbox)

    get_mock = AsyncMock(return_value=stale_cached)
    delete_mock = AsyncMock(return_value=True)
    set_mock = AsyncMock(return_value=True)

    monkeypatch.setattr(cache_manager, "get", get_mock)
    monkeypatch.setattr(cache_manager, "delete", delete_mock)
    monkeypatch.setattr(cache_manager, "set", set_mock)

    result = await agent.process({
        "query_topic": "Predict HDFCBANK price for next 30 days",
        "stock_symbol": "HDFCBANK.NS",
    })

    assert sandbox.calls == 1
    assert result["success"] is True
    assert len(result.get("images", [])) == 1
    delete_mock.assert_awaited_once()
    set_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_prediction_with_no_chart_artifact_returns_failure(monkeypatch):
    sandbox = DummySandbox({
        "success": True,
        "stdout": "run completed",
        "stderr": "",
        "images": [],
    })
    agent = CodeAgent(sandbox)

    monkeypatch.setattr(cache_manager, "get", AsyncMock(return_value=None))
    set_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(cache_manager, "set", set_mock)

    result = await agent.process({
        "query_topic": "Predict HDFCBANK price for next 30 days",
        "stock_symbol": "HDFCBANK.NS",
    })

    assert sandbox.calls == 1
    assert result["success"] is False
    assert "no chart image artifact" in (result.get("error") or "").lower()
    set_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_prediction_failure_uses_stdout_when_stderr_empty(monkeypatch):
    sandbox = DummySandbox({
        "success": False,
        "stdout": "Fetching stock data for HDFCBANK.NS...\nNo data found for HDFCBANK.NS\n",
        "stderr": "",
        "return_code": 1,
        "images": [],
    })
    agent = CodeAgent(sandbox)

    monkeypatch.setattr(cache_manager, "get", AsyncMock(return_value=None))

    result = await agent.process({
        "query_topic": "Predict HDFCBANK price for next 30 days",
        "stock_symbol": "HDFCBANK.NS",
    })

    assert sandbox.calls == 1
    assert result["success"] is False
    assert "no data found" in (result.get("error") or "").lower()


@pytest.mark.asyncio
async def test_lstm_missing_tensorflow_falls_back_to_linear(monkeypatch):
    sandbox = SequenceSandbox([
        {
            "success": False,
            "stdout": "",
            "stderr": "Error: TensorFlow not installed. Please install: pip install tensorflow",
            "return_code": 1,
            "images": [],
        },
        {
            "success": True,
            "stdout": "linear fallback ok",
            "stderr": "",
            "return_code": 0,
            "images": [{"name": "linear_regression_prediction.png", "base64": "abc"}],
        },
    ])
    agent = CodeAgent(sandbox)

    monkeypatch.setattr(cache_manager, "get", AsyncMock(return_value=None))
    set_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(cache_manager, "set", set_mock)
    monkeypatch.setattr(cache_manager, "delete", AsyncMock(return_value=True))

    result = await agent.process({
        "query_topic": "Predict HDFCBANK price next 30 days using LSTM",
        "stock_symbol": "HDFCBANK.NS",
    })

    assert sandbox.calls == 2
    assert result["success"] is True
    assert result["model_type"] == "LINEAR_REGRESSION"
    assert len(result.get("images", [])) == 1


@pytest.mark.asyncio
async def test_prediction_returns_chart_when_images_exist_even_if_exit_nonzero(monkeypatch):
    sandbox = DummySandbox({
        "success": False,
        "stdout": "plot generated",
        "stderr": "TypeError: unsupported format string passed to Series.__format__",
        "return_code": 1,
        "images": [{"name": "linear_regression_prediction.png", "base64": "abc"}],
    })
    agent = CodeAgent(sandbox)

    monkeypatch.setattr(cache_manager, "get", AsyncMock(return_value=None))

    result = await agent.process({
        "query_topic": "Predict HDFCBANK price next 30 days",
        "stock_symbol": "HDFCBANK.NS",
    })

    assert sandbox.calls == 1
    assert result["success"] is True
    assert len(result.get("images", [])) == 1
    assert result.get("model_type") == "LINEAR_REGRESSION"
