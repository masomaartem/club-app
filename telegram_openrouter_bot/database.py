import logging
from typing import List, Dict, Any, Optional
import aiosqlite

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Initialize tables and enable WAL mode for high performance."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")

            # Table for user state, summary, and message counter
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    summary TEXT DEFAULT '',
                    message_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Table for active messages
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                );
                """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id, id);
                """
            )

            await db.commit()
            logger.info("База даних успішно ініціалізована за шляхом: %s", self.db_path)

    async def get_or_create_user(self, user_id: int) -> Dict[str, Any]:
        """Fetch user record or create one if not exists."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)

            await db.execute(
                "INSERT INTO users (user_id, summary, message_count) VALUES (?, '', 0)",
                (user_id,),
            )
            await db.commit()
            return {"user_id": user_id, "summary": "", "message_count": 0}

    async def add_message(self, user_id: int, role: str, content: str) -> int:
        """
        Add message to active history and increment message_count.
        Returns the new message_count.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Ensure user exists
            await db.execute(
                """
                INSERT INTO users (user_id, summary, message_count)
                VALUES (?, '', 0)
                ON CONFLICT(user_id) DO NOTHING;
                """,
                (user_id,),
            )

            # Insert message
            await db.execute(
                "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content),
            )

            # Increment message counter
            await db.execute(
                """
                UPDATE users
                SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (user_id,),
            )
            await db.commit()

            cursor = await db.execute("SELECT message_count FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else 1

    async def get_active_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Get all active messages for user in chronological order."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id ASC",
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [{"role": row["role"], "content": row["content"]} for row in rows]

    async def get_user_summary(self, user_id: int) -> str:
        """Get current summarized context for user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT summary FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row and row[0] else ""

    async def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Get current user summary, counter and total active messages."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT summary, message_count FROM users WHERE user_id = ?", (user_id,))
            user_row = await cursor.fetchone()

            cursor = await db.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,))
            msg_count_row = await cursor.fetchone()

            return {
                "summary": user_row["summary"] if user_row else "",
                "message_count": user_row["message_count"] if user_row else 0,
                "active_messages_count": msg_count_row[0] if msg_count_row else 0,
            }

    async def apply_compression(self, user_id: int, new_summary: str, keep_count: int) -> None:
        """
        Save the new summary, reset message counter, and prune old messages,
        keeping only the last `keep_count` messages in history.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Delete old messages, keeping the latest keep_count messages
            await db.execute(
                """
                DELETE FROM messages
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM messages
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                );
                """,
                (user_id, user_id, keep_count),
            )

            # Update summary and reset counter for next 50 messages
            await db.execute(
                """
                UPDATE users
                SET summary = ?, message_count = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?;
                """,
                (new_summary, user_id),
            )
            await db.commit()
            logger.info("Успішно стиснуто контекст для користувача %d. Залишено %d повідомлень.", user_id, keep_count)

    async def clear_chat(self, user_id: int) -> None:
        """
        Clear all messages, summary, and message count for the user.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await db.execute(
                """
                UPDATE users
                SET summary = '', message_count = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?;
                """,
                (user_id,),
            )
            await db.commit()
            logger.info("Очищено історію та підсумок для користувача %d.", user_id)
