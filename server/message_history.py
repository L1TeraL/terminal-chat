import sqlite3
import datetime

class MessageHistory:
    def __init__(self, db_name='chat_messages.db'):
        self.db_name = db_name
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _create_table(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
                )
                """
            )

    def add_message(self, username: str, message: str):
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_messages (username, message, created_at) 
                VALUES (?, ?, ?)
                """, (username, message, created_at)
            )
            conn.commit()

    def get_chat_history(self, limit: int = 20):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, message, created_at
                FROM chat_messages
                ORDER BY id DESC
                LIMIT ?
                """, (limit, )
            )


            rows = cursor.fetchall()

        return rows[::-1]