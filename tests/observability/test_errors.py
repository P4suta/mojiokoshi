"""Tests for :mod:`mojiokoshi.observability.errors`."""

from __future__ import annotations

import deal
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from mojiokoshi.observability.errors import register_exception_handlers


class _Echo(BaseModel):
    n: int


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/echo")
    def echo(body: _Echo) -> dict[str, int]:
        return {"n": body.n}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("this is fine")

    @app.get("/http-error")
    def http_error() -> None:
        raise HTTPException(status_code=404, detail="no such thing")

    @deal.pre(lambda x: x > 0, message="x must be positive")
    def _positive(x: int) -> int:
        return x

    @app.get("/contract/{x}")
    def contract(x: int) -> dict[str, int]:
        return {"x": _positive(x)}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _assert_problem(body: dict, *, status: int, title: str) -> None:
    assert body["status"] == status
    assert body["title"] == title
    assert body["type"].startswith("https://errors.mojiokoshi/")
    assert isinstance(body["trace_id"], str)
    assert len(body["trace_id"]) > 0


class TestValidationError:
    def test_returns_422_with_problem_details(self, client: TestClient):
        resp = client.post("/echo", json={"n": "not-an-int"})
        assert resp.status_code == 422
        body = resp.json()
        _assert_problem(body, status=422, title="Validation failed")
        assert isinstance(body["detail"], list)

    def test_x_request_id_header_round_trips(self, client: TestClient):
        resp = client.post(
            "/echo",
            json={"n": "not-an-int"},
            headers={"X-Request-ID": "trace-42"},
        )
        assert resp.headers.get("x-request-id") == "trace-42"
        assert resp.json()["trace_id"] == "trace-42"

    def test_trace_id_generated_when_header_missing(self, client: TestClient):
        resp = client.post("/echo", json={"n": "bad"})
        # UUID4 is 36 chars; accept anything non-empty and present in the header.
        trace_id = resp.json()["trace_id"]
        assert trace_id
        assert resp.headers.get("x-request-id") == trace_id


class TestHTTPException:
    def test_passes_status_and_detail_through(self, client: TestClient):
        resp = client.get("/http-error")
        assert resp.status_code == 404
        body = resp.json()
        _assert_problem(body, status=404, title="HTTP error")
        assert body["detail"] == "no such thing"


class TestDealContract:
    def test_precondition_failure_returns_422(self, client: TestClient):
        resp = client.get("/contract/0")  # violates x > 0
        assert resp.status_code == 422
        body = resp.json()
        _assert_problem(body, status=422, title="Precondition violation")
        assert "must be positive" in body["detail"]

    def test_valid_call_still_works(self, client: TestClient):
        resp = client.get("/contract/5")
        assert resp.status_code == 200
        assert resp.json() == {"x": 5}


class TestUnhandledException:
    def test_returns_500_problem(self, client: TestClient):
        resp = client.get("/boom")
        assert resp.status_code == 500
        body = resp.json()
        _assert_problem(body, status=500, title="Internal server error")
        assert body["detail"] is None
