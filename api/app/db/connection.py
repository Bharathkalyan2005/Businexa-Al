"""Database connection helper using pure-Python pg8000 pointed at Neon Postgres."""

from __future__ import annotations

import asyncio
import os
import ssl
from typing import Any
from urllib.parse import parse_qs, urlparse

import pg8000.native

from app.config import settings


class DatabasePool:
    """Async database interface backed by pg8000."""

    _instance: DatabasePool | None = None

    @classmethod
    def instance(cls) -> DatabasePool:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_connection(self) -> pg8000.native.Connection:
        parsed = urlparse(settings.database_url)
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        return pg8000.native.Connection(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
            ssl_context=ssl_ctx,
        )

    async def connect(self) -> None:
        """Validate connection."""
        pass

    async def disconnect(self) -> None:
        pass

    def _convert_query(self, query: str) -> str:
        # Convert Postgres $1, $2 to pg8000 :p1, :p2 or run directly
        # pg8000 native allows param positional by converting $1 -> :1, $2 -> :2
        # but native.Connection.run() supports parameters directly!
        return query

    async def fetch_one(self, query: str, *args: object) -> dict[str, Any] | None:
        def _run():
            conn = self._get_connection()
            try:
                # Convert $1, $2, $3 to ? for pg8000 or format
                # In pg8000.native: conn.run("SELECT ... WHERE id = :id", id=val)
                # Or param array replacement:
                sql = query
                params = {}
                for idx, val in enumerate(args, 1):
                    sql = sql.replace(f"${idx}", f":p{idx}")
                    params[f"p{idx}"] = str(val) if isinstance(val, (int, float, str)) else val

                rows = conn.run(sql, **params)
                if not rows:
                    return None
                col_names = [col["name"] for col in conn.columns]
                return dict(zip(col_names, rows[0]))
            finally:
                conn.close()

        return await asyncio.to_thread(_run)

    async def fetch_all(self, query: str, *args: object) -> list[dict[str, Any]]:
        def _run():
            conn = self._get_connection()
            try:
                sql = query
                params = {}
                for idx, val in enumerate(args, 1):
                    sql = sql.replace(f"${idx}", f":p{idx}")
                    params[f"p{idx}"] = str(val) if isinstance(val, (int, float, str)) else val

                rows = conn.run(sql, **params)
                if not rows:
                    return []
                col_names = [col["name"] for col in conn.columns]
                return [dict(zip(col_names, row)) for row in rows]
            finally:
                conn.close()

        return await asyncio.to_thread(_run)

    async def execute(self, query: str, *args: object) -> str:
        def _run():
            conn = self._get_connection()
            try:
                sql = query
                params = {}
                for idx, val in enumerate(args, 1):
                    sql = sql.replace(f"${idx}", f":p{idx}")
                    params[f"p{idx}"] = str(val) if isinstance(val, (int, float, str)) else val

                conn.run(sql, **params)
                return "SUCCESS"
            finally:
                conn.close()

        return await asyncio.to_thread(_run)
