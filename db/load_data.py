import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from datetime import datetime

import asyncpg

from bot.config import DATABASE_URL


VIDEO_INSERT_SQL = """
INSERT INTO videos (
    id,
    creator_id,
    video_created_at,
    views_count,
    likes_count,
    comments_count,
    reports_count,
    created_at,
    updated_at
)
VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9
)
"""

SNAPSHOT_INSERT_SQL = """
INSERT INTO video_snapshots (
    id,
    video_id,
    views_count,
    likes_count,
    comments_count,
    reports_count,
    delta_views_count,
    delta_likes_count,
    delta_comments_count,
    delta_reports_count,
    created_at,
    updated_at
)
VALUES (
    $1, $2,
    $3, $4, $5, $6,
    $7, $8, $9, $10,
    $11, $12
)
"""


def parse_datetime(value: str) -> datetime:
    """
    Преобразует ISO-строку из JSON в datetime.
    JSON содержит строки вида '2025-08-19T08:54:35+00:00'.
    """
    return datetime.fromisoformat(value)


async def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


async def clear_tables(conn: asyncpg.Connection) -> None:
    """
    Полная очистка таблиц перед загрузкой.
    Упрощает повторные прогоны и исключает дубли.
    """
    await conn.execute("TRUNCATE video_snapshots, videos CASCADE;")


async def insert_videos(
    conn: asyncpg.Connection,
    videos: list[dict[str, Any]],
) -> None:
    rows = []

    for video in videos:
        rows.append(
            (
                video["id"],
                video["creator_id"],
                parse_datetime(video["video_created_at"]),
                video["views_count"],
                video["likes_count"],
                video["comments_count"],
                video["reports_count"],
                parse_datetime(video["created_at"]),
                parse_datetime(video["updated_at"]),
            )
        )

    await conn.executemany(VIDEO_INSERT_SQL, rows)


async def insert_snapshots(
    conn: asyncpg.Connection,
    videos: list[dict[str, Any]],
) -> None:
    rows = []

    for video in videos:
        for snapshot in video.get("snapshots", []):
            rows.append(
                (
                    snapshot["id"],
                    snapshot["video_id"],
                    snapshot["views_count"],
                    snapshot["likes_count"],
                    snapshot["comments_count"],
                    snapshot["reports_count"],
                    snapshot["delta_views_count"],
                    snapshot["delta_likes_count"],
                    snapshot["delta_comments_count"],
                    snapshot["delta_reports_count"],
                    parse_datetime(snapshot["created_at"]),
                    parse_datetime(snapshot["updated_at"]),
                )
            )

    await conn.executemany(SNAPSHOT_INSERT_SQL, rows)


async def main(json_path: Path) -> None:
    print(f"Loading data from {json_path}")

    data = await load_json(json_path)
    videos = data.get("videos", [])

    if not videos:
        raise ValueError("JSON does not contain 'videos' or it's empty")

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        async with conn.transaction():
            await clear_tables(conn)
            await insert_videos(conn, videos)
            await insert_snapshots(conn, videos)
    finally:
        await conn.close()

    print(f"Loaded {len(videos)} videos successfully")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m db.load_data <path_to_json>")
        sys.exit(1)

    asyncio.run(main(Path(sys.argv[1])))
