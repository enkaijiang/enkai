import logging
import ntpath
import os
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("everything-dify-bridge")
load_dotenv()


def _parse_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} 必须是整数，当前值：{raw_value}") from exc


def _parse_allowed_roots() -> list[str]:
    raw_value = os.getenv("EVERYTHING_ALLOWED_ROOTS", "").strip()
    if not raw_value:
        return []

    roots: list[str] = []
    for item in raw_value.split(";"):
        value = item.strip()
        if not value:
            continue
        normalized = ntpath.normcase(ntpath.normpath(value)).rstrip("\\")
        roots.append(normalized)
    return roots


class Settings:
    def __init__(self) -> None:
        self.base_url = os.getenv("EVERYTHING_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
        self.username = os.getenv("EVERYTHING_USERNAME", "").strip()
        self.password = os.getenv("EVERYTHING_PASSWORD", "").strip()
        self.timeout_seconds = _parse_int("EVERYTHING_TIMEOUT_SECONDS", 10)
        self.default_count = _parse_int("EVERYTHING_DEFAULT_COUNT", 10)
        self.max_count = _parse_int("EVERYTHING_MAX_COUNT", 50)
        self.allowed_roots = _parse_allowed_roots()

        if self.default_count <= 0:
            raise RuntimeError("EVERYTHING_DEFAULT_COUNT 必须大于 0")
        if self.max_count <= 0:
            raise RuntimeError("EVERYTHING_MAX_COUNT 必须大于 0")
        if self.default_count > self.max_count:
            raise RuntimeError("EVERYTHING_DEFAULT_COUNT 不能大于 EVERYTHING_MAX_COUNT")

    @property
    def auth(self) -> tuple[str, str] | None:
        if not self.username:
            return None
        return self.username, self.password


settings = Settings()

app = FastAPI(
    title="Everything Dify Bridge",
    version="1.0.0",
    description=(
        "把 Everything HTTP 搜索能力包装成一个更适合 Dify Custom Tool 调用的接口。"
        "建议只暴露白名单目录，不要直接把原始 Everything HTTP 地址交给 Dify。"
    ),
)


def _build_full_path(path_value: str, name_value: str) -> str:
    path_value = (path_value or "").strip()
    name_value = (name_value or "").strip()
    if path_value and name_value:
        return ntpath.join(path_value, name_value)
    return path_value or name_value


def _is_path_allowed(full_path: str) -> bool:
    if not settings.allowed_roots:
        return True
    if not full_path:
        return False

    normalized_path = ntpath.normcase(ntpath.normpath(full_path)).rstrip("\\")
    for root in settings.allowed_roots:
        if normalized_path == root or normalized_path.startswith(f"{root}\\"):
            return True
    return False


def _fetch_everything(params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(
            url=f"{settings.base_url}/",
            params=params,
            auth=settings.auth,
            timeout=settings.timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("调用 Everything 失败")
        raise HTTPException(status_code=502, detail=f"调用 Everything 失败：{exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Everything 返回的不是合法 JSON") from exc

    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Everything 返回结构异常")

    return data


@app.get("/", operation_id="index")
def index() -> dict[str, Any]:
    return {
        "service": "everything-dify-bridge",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/health",
        "search": "/search?query=demo",
    }


@app.get("/health", operation_id="healthCheck")
def health(check_upstream: bool = Query(default=True, description="是否探测 Everything 上游连通性")) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "ok",
        "service": "everything-dify-bridge",
        "everything_base_url": settings.base_url,
        "default_count": settings.default_count,
        "max_count": settings.max_count,
        "allowed_roots": settings.allowed_roots,
    }

    if not check_upstream:
        return payload

    try:
        data = _fetch_everything(
            {
                "search": "",
                "json": 1,
                "count": 1,
            }
        )
        payload["upstream"] = {
            "reachable": True,
            "total_results": data.get("totalResults"),
        }
    except HTTPException as exc:
        payload["status"] = "degraded"
        payload["upstream"] = {
            "reachable": False,
            "error": exc.detail,
        }

    return payload


@app.get("/search", operation_id="searchFiles")
def search(
    query: str = Query(..., min_length=1, description="Everything 搜索词"),
    count: int | None = Query(default=None, ge=1, description="返回条数"),
    regex: bool = Query(default=False, description="是否开启正则"),
    case_sensitive: bool = Query(default=False, description="是否区分大小写"),
    whole_word: bool = Query(default=False, description="是否整词匹配"),
    path_match: bool = Query(default=False, description="是否按完整路径匹配"),
    sort: str = Query(default="name", description="排序字段：name、path、size、date_modified"),
    ascending: bool = Query(default=True, description="是否升序"),
) -> dict[str, Any]:
    requested_count = count or settings.default_count
    safe_count = min(requested_count, settings.max_count)
    safe_sort = sort if sort in {"name", "path", "size", "date_modified"} else "name"

    data = _fetch_everything(
        {
            "search": query,
            "json": 1,
            "count": safe_count,
            "offset": 0,
            "path_column": 1,
            "size_column": 1,
            "date_modified_column": 1,
            "sort": safe_sort,
            "ascending": 1 if ascending else 0,
            "regex": 1 if regex else 0,
            "case": 1 if case_sensitive else 0,
            "wholeword": 1 if whole_word else 0,
            "path": 1 if path_match else 0,
        }
    )

    raw_results = data.get("results", [])
    if not isinstance(raw_results, list):
        raise HTTPException(status_code=502, detail="Everything 返回 results 字段异常")

    items: list[dict[str, Any]] = []
    filtered_out = 0

    for raw_item in raw_results:
        if not isinstance(raw_item, dict):
            continue

        name_value = str(raw_item.get("name", "") or "")
        path_value = str(raw_item.get("path", "") or "")
        full_path = _build_full_path(path_value, name_value)

        if not _is_path_allowed(full_path):
            filtered_out += 1
            continue

        items.append(
            {
                "type": raw_item.get("type", "file"),
                "name": name_value,
                "path": path_value,
                "full_path": full_path,
                "size": raw_item.get("size"),
                "date_modified": raw_item.get("date_modified"),
            }
        )

    return {
        "query": query,
        "returned_results": len(items),
        "upstream_returned_results": len(raw_results),
        "upstream_total_results": data.get("totalResults", len(raw_results)),
        "filtered_out_by_allowed_roots": filtered_out,
        "count_limit": safe_count,
        "sort": safe_sort,
        "ascending": ascending,
        "items": items,
    }
