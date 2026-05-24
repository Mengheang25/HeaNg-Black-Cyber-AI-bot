# -*- coding: utf-8 -*-
import asyncio
import html
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Set UTF-8 encoding for output
if sys.stdout.encoding is None or "utf" not in sys.stdout.encoding.lower():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables from .env file
load_dotenv()


def get_int_env(name, default):
    """Safely parse integer environment variables."""
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


# Secure Configuration - Load from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek/deepseek-v4-flash")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
DATABASE_PATH = os.getenv("DATABASE_PATH", "date_user.db")
ENABLE_HISTORY = os.getenv("ENABLE_HISTORY", "true").lower() == "true"
ACTIVE_USER_WINDOW_MINUTES = max(1, get_int_env("ACTIVE_USER_WINDOW_MINUTES", 30))
USER_PAGE_SIZE = 8
USER_HOURLY_LIMIT = max(1, get_int_env("USER_HOURLY_LIMIT", 5))
RATE_LIMIT_WINDOW_HOURS = max(1, get_int_env("RATE_LIMIT_WINDOW_HOURS", 1))
CONTEXT_WINDOW_MESSAGES = max(0, get_int_env("CONTEXT_WINDOW_MESSAGES", 10))
API_MAX_RETRIES = max(1, get_int_env("API_MAX_RETRIES", 2))
API_RETRY_DELAY_SECONDS = max(1, get_int_env("API_RETRY_DELAY_SECONDS", 2))
API_TIMEOUT_SECONDS = max(5, get_int_env("API_TIMEOUT_SECONDS", 60))

# Validate required environment variables
if not TELEGRAM_TOKEN or not OPENROUTER_KEY:
    sys.stderr.write("ERROR: Missing required environment variables. Please check your .env file.\n")
    sys.exit(1)

# Load system prompt
try:
    with open("system-prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    sys.stderr.write("WARNING: system-prompt.txt not found. Using default prompt.\n")
    SYSTEM_PROMPT = "You are a helpful AI assistant."

# Admin Configuration - Set your admin user IDs here
ADMIN_IDS = {
    int(admin_id)
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip()
}

# Pending admin actions tracker
pending_admin_actions = {}
user_last_messages = {}

# Decorative strings for reuse
BLOCKED_MESSAGE = "Your access to this bot is currently blocked. Please contact the admin."
RATE_LIMIT_REACHED_MESSAGE = "Rate limit reached for this user."

# ═══════════════════════════════════════════════════════════════════════
# DATABASE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════


class ConversationDB:
    """Manage users, conversation history, and rate limits in SQLite."""

    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _compose_where_clause(self, conditions=None, params=None, exclude_user_ids=None):
        conditions = list(conditions or [])
        params = list(params or [])
        excluded_ids = [int(user_id) for user_id in (exclude_user_ids or [])]

        if excluded_ids:
            placeholders = ",".join("?" for _ in excluded_ids)
            conditions.append(f"user_id NOT IN ({placeholders})")
            params.extend(excluded_ids)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return where_clause, params

    def init_db(self):
        """Initialize database tables and migrate legacy schema."""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    is_blocked INTEGER DEFAULT 0,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_quota_grants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    extra_questions INTEGER NOT NULL,
                    granted_hours INTEGER NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    granted_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_rate_limit_events_user_created_at
                ON rate_limit_events(user_id, created_at)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_quota_grants_user_expires_at
                ON user_quota_grants(user_id, expires_at)
                """
            )

            self._migrate_users_table(cursor)

            conn.commit()
            conn.close()
            print("[OK] Database initialized successfully")
        except Exception as e:
            sys.stderr.write(f"[ERROR] Database initialization error: {e}\n")

    def _migrate_users_table(self, cursor):
        """Add missing columns for older user tables."""
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cursor.fetchall()}

        if "first_name" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
        if "username" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "is_blocked" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
        if "last_active" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        if "created_at" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        cursor.execute(
            """
            UPDATE users
            SET
                is_blocked = COALESCE(is_blocked, 0),
                last_active = COALESCE(last_active, created_at, CURRENT_TIMESTAMP),
                created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            """
        )

    def add_user(self, user_id, first_name=None, username=None):
        """Insert or refresh a user row."""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO users (user_id, first_name, username, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name = COALESCE(excluded.first_name, users.first_name),
                    username = COALESCE(excluded.username, users.username),
                    last_active = CURRENT_TIMESTAMP
                """,
                (user_id, first_name, username),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error adding user: {e}\n")

    def save_message(self, user_id, message_type, content):
        """Save user message or AI response to database."""
        if not ENABLE_HISTORY:
            return

        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO conversations (user_id, message_type, content)
                VALUES (?, ?, ?)
                """,
                (user_id, message_type, content),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error saving message: {e}\n")

    def get_user_history(self, user_id, limit=20):
        """Retrieve conversation history for a user."""
        if not ENABLE_HISTORY or limit <= 0:
            return []

        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT message_type, content, timestamp
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )

            messages = cursor.fetchall()
            conn.close()
            return messages[::-1]
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error retrieving history: {e}\n")
            return []

    def clear_user_history(self, user_id):
        """Delete all conversation history for a user."""
        if not ENABLE_HISTORY:
            return False

        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM conversations
                WHERE user_id = ?
                """,
                (user_id,),
            )

            conn.commit()
            rows_deleted = cursor.rowcount
            conn.close()
            return rows_deleted > 0
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error clearing history: {e}\n")
            return False

    def record_rate_limit_event(self, user_id):
        """Record a processed user request for rate limiting."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rate_limit_events (user_id)
                VALUES (?)
                """,
                (user_id,),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error recording rate limit event: {e}\n")

    def grant_user_quota(self, user_id, extra_questions, hours, granted_by=None):
        """Grant temporary bonus questions to a user."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_quota_grants (
                    user_id,
                    extra_questions,
                    granted_hours,
                    expires_at,
                    granted_by
                )
                VALUES (?, ?, ?, datetime('now', ?), ?)
                """,
                (user_id, extra_questions, hours, f"+{hours} hours", granted_by),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error granting user quota: {e}\n")
            return False

    def get_user_rate_limit_status(
        self,
        user_id,
        base_limit=USER_HOURLY_LIMIT,
        window_hours=RATE_LIMIT_WINDOW_HOURS,
    ):
        """Return usage and remaining quota for a user."""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) AS usage_count, MIN(created_at) AS oldest_recent
                FROM rate_limit_events
                WHERE user_id = ?
                  AND datetime(created_at) >= datetime('now', ?)
                """,
                (user_id, f"-{window_hours} hours"),
            )
            usage_row = cursor.fetchone()
            used_count = int(usage_row["usage_count"] or 0)
            oldest_recent = usage_row["oldest_recent"]

            cursor.execute(
                """
                SELECT COALESCE(SUM(extra_questions), 0) AS bonus_count
                FROM user_quota_grants
                WHERE user_id = ?
                  AND datetime(expires_at) > datetime('now')
                """,
                (user_id,),
            )
            bonus_row = cursor.fetchone()
            bonus_count = int(bonus_row["bonus_count"] or 0)

            cursor.execute(
                """
                SELECT extra_questions, granted_hours, expires_at, created_at
                FROM user_quota_grants
                WHERE user_id = ?
                  AND datetime(expires_at) > datetime('now')
                ORDER BY datetime(expires_at) ASC, id ASC
                """,
                (user_id,),
            )
            grants = [
                {
                    "extra_questions": int(row["extra_questions"] or 0),
                    "granted_hours": int(row["granted_hours"] or 0),
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"],
                }
                for row in cursor.fetchall()
            ]

            conn.close()

            total_limit = base_limit + bonus_count
            remaining = max(0, total_limit - used_count)

            return {
                "base_limit": base_limit,
                "window_hours": window_hours,
                "used_count": used_count,
                "bonus_count": bonus_count,
                "total_limit": total_limit,
                "remaining": remaining,
                "oldest_recent": oldest_recent,
                "active_grants": grants,
            }
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error retrieving user rate status: {e}\n")
            return {
                "base_limit": base_limit,
                "window_hours": window_hours,
                "used_count": 0,
                "bonus_count": 0,
                "total_limit": base_limit,
                "remaining": base_limit,
                "oldest_recent": None,
                "active_grants": [],
            }

    def get_total_users(self, exclude_user_ids=None):
        """Return total registered users."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            where_clause, params = self._compose_where_clause(exclude_user_ids=exclude_user_ids)
            cursor.execute(f"SELECT COUNT(*) FROM users{where_clause}", params)
            total = cursor.fetchone()[0]
            conn.close()
            return total
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error counting users: {e}\n")
            return 0

    def get_blocked_user_count(self, exclude_user_ids=None):
        """Return blocked user count."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            where_clause, params = self._compose_where_clause(
                conditions=["COALESCE(is_blocked, 0) = 1"],
                exclude_user_ids=exclude_user_ids,
            )
            cursor.execute(f"SELECT COUNT(*) FROM users{where_clause}", params)
            total = cursor.fetchone()[0]
            conn.close()
            return total
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error counting blocked users: {e}\n")
            return 0

    def get_active_user_count(self, minutes=ACTIVE_USER_WINDOW_MINUTES, exclude_user_ids=None):
        """Return users active within the last N minutes."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            where_clause, params = self._compose_where_clause(
                conditions=[
                    "COALESCE(is_blocked, 0) = 0",
                    "datetime(last_active) >= datetime('now', ?)",
                ],
                params=[f"-{minutes} minutes"],
                exclude_user_ids=exclude_user_ids,
            )
            cursor.execute(f"SELECT COUNT(*) FROM users{where_clause}", params)
            total = cursor.fetchone()[0]
            conn.close()
            return total
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error counting active users: {e}\n")
            return 0

    def get_users_page(self, page=0, page_size=USER_PAGE_SIZE, exclude_user_ids=None):
        """Return a page of users and the total user count."""
        page = max(0, page)
        offset = page * page_size

        try:
            conn = self._connect()
            cursor = conn.cursor()

            where_clause, params = self._compose_where_clause(exclude_user_ids=exclude_user_ids)

            cursor.execute(f"SELECT COUNT(*) FROM users{where_clause}", params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f"""
                SELECT user_id, first_name, username, is_blocked, last_active, created_at
                FROM users
                {where_clause}
                ORDER BY datetime(created_at) DESC, user_id DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            )

            users = cursor.fetchall()
            conn.close()
            return users, total
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error retrieving users page: {e}\n")
            return [], 0

    def get_user_details(self, user_id):
        """Return user details and message count."""
        try:
            conn = self._connect()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT user_id, first_name, username, is_blocked, last_active, created_at
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            )
            user = cursor.fetchone()

            if not user:
                conn.close()
                return None

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM conversations
                WHERE user_id = ?
                """,
                (user_id,),
            )
            message_count = cursor.fetchone()[0]
            conn.close()

            return {
                "user_id": user["user_id"],
                "first_name": user["first_name"],
                "username": user["username"],
                "is_blocked": bool(user["is_blocked"]),
                "last_active": user["last_active"],
                "created_at": user["created_at"],
                "message_count": message_count,
            }
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error retrieving user details: {e}\n")
            return None

    def set_user_blocked(self, user_id, blocked=True):
        """Block or unblock a user."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET is_blocked = ?
                WHERE user_id = ?
                """,
                (1 if blocked else 0, user_id),
            )
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error updating block status: {e}\n")
            return False

    def is_user_blocked(self, user_id):
        """Check whether a user is blocked."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(is_blocked, 0) FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return bool(row[0]) if row else False
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error checking block status: {e}\n")
            return False

    def get_broadcast_recipients(self, exclude_user_ids=None):
        """Return user IDs eligible for admin broadcasts."""
        try:
            conn = self._connect()
            cursor = conn.cursor()
            where_clause, params = self._compose_where_clause(
                conditions=["COALESCE(is_blocked, 0) = 0"],
                exclude_user_ids=exclude_user_ids,
            )
            cursor.execute(f"SELECT user_id FROM users{where_clause} ORDER BY user_id ASC", params)
            user_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            return user_ids
        except Exception as e:
            sys.stderr.write(f"[ERROR] Error retrieving broadcast recipients: {e}\n")
            return []


# Initialize database
db = ConversationDB()

# ═══════════════════════════════════════════════════════════════════════
# DECORATIVE SYMBOLS AND STYLES
# ═══════════════════════════════════════════════════════════════════════

DECORATIONS = {
    "arrow": "➤",
    "lightning": "⚡",
    "line_heavy": "═" * 45,
    "line_medium": "─" * 45,
    "line_light": "╌" * 45,
    "skull": "☠️",
    "bracket_open": "『",
    "bracket_close": "』",
    "star": "✦",
    "diamond": "◆",
    "cross": "✖",
    "check": "✔",
    "fire": "🔥",
    "bolt": "⚡",
    "crown": "♛",
    "gem": "💎",
}


def to_math_sans_serif_bold(text):
    """Convert text to Mathematical Sans-Serif Bold Unicode characters."""
    result = []
    for char in text:
        if "A" <= char <= "Z":
            result.append(chr(0x1D5D4 + ord(char) - ord("A")))
        elif "a" <= char <= "z":
            result.append(chr(0x1D5EE + ord(char) - ord("a")))
        elif "0" <= char <= "9":
            result.append(chr(0x1D7EC + ord(char) - ord("0")))
        else:
            result.append(char)

    return "".join(result)


def style_heading(text):
    """Render section headings in Mathematical Sans-Serif Bold."""
    return to_math_sans_serif_bold(text)


def style_markdown_text(text):
    """Render text in Mathematical Sans-Serif Bold and escape markdown brackets."""
    styled = to_math_sans_serif_bold(text)
    return styled.replace("[", "\\[").replace("]", "\\]")


def build_conversation_messages(user_id, prompt):
    """Build the context window sent to the model."""
    messages = []

    for history_item in db.get_user_history(user_id, limit=CONTEXT_WINDOW_MESSAGES):
        msg_type = history_item["message_type"]
        content = history_item["content"]

        if not content:
            continue

        if msg_type == "user":
            messages.append({"role": "user", "content": content})
        elif msg_type == "ai":
            messages.append({"role": "assistant", "content": content})

    messages.append({"role": "user", "content": prompt})
    return messages


def ask_model(messages):
    """Call the model with one retry on failure."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    }

    last_error = "Unknown API error"

    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=API_TIMEOUT_SECONDS,
            )

            print(f"[INFO] API Status Code: {response.status_code} (attempt {attempt}/{API_MAX_RETRIES})")

            try:
                response_json = response.json()
            except ValueError as exc:
                raise RuntimeError("Invalid JSON response from API.") from exc

            if "error" in response_json:
                error_info = response_json["error"]
                if isinstance(error_info, dict):
                    error_message = error_info.get("message") or str(error_info)
                else:
                    error_message = str(error_info)
                raise RuntimeError(f"API Error: {error_message}")

            choices = response_json.get("choices")
            if not choices:
                raise RuntimeError(f"Unexpected response format: {response_json}")

            content = choices[0]["message"]["content"]
            if not content:
                raise RuntimeError("Empty response returned by API.")

            return content
        except (requests.RequestException, RuntimeError, KeyError, IndexError, TypeError) as exc:
            last_error = str(exc)
            print(f"[ERROR] API call failed on attempt {attempt}: {last_error}")
            if attempt < API_MAX_RETRIES:
                time.sleep(API_RETRY_DELAY_SECONDS)
                continue
            raise RuntimeError(last_error)


def format_timestamp(value):
    """Format SQLite timestamps for display."""
    if not value:
        return "-"

    try:
        return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(value)


def format_username(username):
    """Format Telegram usernames consistently."""
    if not username:
        return "-"
    return username if username.startswith("@") else f"@{username}"


def get_display_name(first_name, username, user_id=None):
    """Return the best available display name."""
    if first_name:
        return first_name
    if username:
        return format_username(username)
    if user_id is not None:
        return f"User {user_id}"
    return "Unknown"


def register_user(telegram_user):
    """Track the latest user metadata and activity timestamp."""
    if not telegram_user:
        return
    db.add_user(telegram_user.id, telegram_user.first_name, telegram_user.username)


def is_admin(user_id):
    """Check admin access."""
    return user_id in ADMIN_IDS


def get_pending_admin_action(admin_user_id):
    """Return pending admin action state."""
    return pending_admin_actions.get(admin_user_id)


def set_pending_admin_action(admin_user_id, action_type):
    """Set a pending admin action state."""
    pending_admin_actions[admin_user_id] = {"type": action_type}


def clear_pending_admin_action(admin_user_id):
    """Clear a pending admin action state."""
    pending_admin_actions.pop(admin_user_id, None)


def get_pending_admin_action_text(admin_user_id):
    """Return dashboard hint for pending admin actions."""
    action = get_pending_admin_action(admin_user_id)
    if not action:
        return None

    if action["type"] == "broadcast":
        return "Broadcast mode: waiting for your next text message."
    if action["type"] == "quota_grant":
        return "Add Questions mode: send user_id-extra_questions-hours."
    return None


async def reply_blocked(update: Update):
    """Notify blocked users that they cannot access the bot."""
    if update.message:
        await update.message.reply_text(BLOCKED_MESSAGE)
    elif update.callback_query:
        await update.callback_query.answer(BLOCKED_MESSAGE, show_alert=True)


async def safe_edit_text(message, text, reply_markup=None, parse_mode=None):
    """Ignore Telegram no-op edit errors for repeated admin clicks."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as exc:
        if "Message is not modified" in str(exc):
            return
        raise


def format_duration(seconds):
    """Format seconds to a short human-readable duration."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return "less than 1 minute"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    parts = []

    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")

    return " ".join(parts) if parts else "less than 1 minute"


def get_rate_limit_reset_hint(oldest_recent, window_hours):
    """Estimate when the next request slot becomes available."""
    if not oldest_recent:
        return None

    try:
        oldest_dt = datetime.fromisoformat(str(oldest_recent))
    except ValueError:
        return None

    reset_at = oldest_dt + timedelta(hours=window_hours)
    seconds_left = (reset_at - datetime.utcnow()).total_seconds()

    if seconds_left <= 0:
        return None

    return format_duration(seconds_left)


def build_active_grants_summary(active_grants):
    """Format active bonus quota grants for display."""
    if not active_grants:
        return "None"

    parts = []
    for grant in active_grants[:3]:
        parts.append(f"+{grant['extra_questions']} until {format_timestamp(grant['expires_at'])}")

    if len(active_grants) > 3:
        parts.append(f"+ {len(active_grants) - 3} more grant(s)")

    return "; ".join(parts)


def build_rate_limit_exceeded_text(status):
    """Build user-facing message when the rate limit is reached."""
    reset_hint = get_rate_limit_reset_hint(status["oldest_recent"], status["window_hours"])
    wait_line = "Please wait until the next available hour window before continuing."

    if reset_hint:
        wait_line = f"Please wait about {reset_hint}, then continue again."

    lines = [
        style_heading(RATE_LIMIT_REACHED_MESSAGE),
        "",
        wait_line,
        f"Allowed: {status['total_limit']} question(s) in {status['window_hours']} hour(s).",
        f"Used: {status['used_count']}",
        f"Remaining: {status['remaining']}",
    ]

    if status["bonus_count"] > 0:
        lines.append(f"Active bonus questions: {status['bonus_count']}")

    return "\n".join(lines)


def parse_quota_grant_text(text):
    """Parse admin grant format: user_id-extra_questions-hours."""
    parts = [part.strip() for part in text.split("-")]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError("Use the format: user_id-extra_questions-hours")

    user_id, extra_questions, hours = [int(part) for part in parts]

    if user_id <= 0 or extra_questions <= 0 or hours <= 0:
        raise ValueError("All values must be positive integers.")

    return user_id, extra_questions, hours


def build_dashboard_text(admin_user_id):
    """Compose the admin dashboard summary."""
    total_users = db.get_total_users(exclude_user_ids=ADMIN_IDS)
    active_users = db.get_active_user_count(
        minutes=ACTIVE_USER_WINDOW_MINUTES,
        exclude_user_ids=ADMIN_IDS,
    )
    blocked_users = db.get_blocked_user_count(exclude_user_ids=ADMIN_IDS)
    pending_text = get_pending_admin_action_text(admin_user_id)

    lines = [
        style_heading("Admin Dashboard"),
        "",
        f"Total users: {total_users}",
        f"Active users ({ACTIVE_USER_WINDOW_MINUTES}m): {active_users}",
        f"Blocked users: {blocked_users}",
        f"User limit: {USER_HOURLY_LIMIT} question(s) / {RATE_LIMIT_WINDOW_HOURS} hour(s)",
    ]

    if pending_text:
        lines.extend(["", pending_text])

    lines.extend(["", "Choose an action below."])
    return "\n".join(lines)


def build_dashboard_keyboard():
    """Keyboard for the admin dashboard."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("User Management", callback_data="admin:users:0")],
            [InlineKeyboardButton("Send Notification", callback_data="admin:broadcast:start")],
            [InlineKeyboardButton("Add Questions", callback_data="admin:grant:start")],
            [InlineKeyboardButton("Refresh", callback_data="admin:dashboard")],
        ]
    )


def build_user_list_keyboard(users, page, total_pages):
    """Keyboard for the user list."""
    keyboard = []
    for user in users:
        label = f"{get_display_name(user['first_name'], user['username'], user['user_id'])} | {user['user_id']}"
        keyboard.append(
            [
                InlineKeyboardButton(
                    label[:60],
                    callback_data=f"admin:user:{user['user_id']}:{page}",
                )
            ]
        )

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("Previous", callback_data=f"admin:users:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data=f"admin:users:{page}"))
        if page + 1 < total_pages:
            nav_row.append(InlineKeyboardButton("Next", callback_data=f"admin:users:{page + 1}"))
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="admin:dashboard")])
    return InlineKeyboardMarkup(keyboard)


def build_user_detail_keyboard(user_id, is_blocked, page):
    """Keyboard for individual user actions."""
    action_label = "Unblock User" if is_blocked else "Block User"
    action_name = "unblock" if is_blocked else "block"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(action_label, callback_data=f"admin:{action_name}:{user_id}:{page}")],
            [InlineKeyboardButton("Back to Users", callback_data=f"admin:users:{page}")],
            [InlineKeyboardButton("Back to Dashboard", callback_data="admin:dashboard")],
        ]
    )


def build_broadcast_keyboard():
    """Keyboard shown while waiting for notification text."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Cancel Notification", callback_data="admin:broadcast:cancel")],
            [InlineKeyboardButton("Back to Dashboard", callback_data="admin:broadcast:cancel")],
        ]
    )


def build_quota_grant_keyboard():
    """Keyboard shown while waiting for quota grant input."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Cancel Add Questions", callback_data="admin:grant:cancel")],
            [InlineKeyboardButton("Back to Dashboard", callback_data="admin:grant:cancel")],
        ]
    )


def build_user_list_text(users, page, total_users):
    """Format the user list body."""
    total_pages = max(1, (total_users + USER_PAGE_SIZE - 1) // USER_PAGE_SIZE)
    lines = [
        style_heading("User Management"),
        f"Total users: {total_users}",
        f"Page: {page + 1}/{total_pages}",
        "",
    ]

    if not users:
        lines.append("No users found yet.")
    else:
        lines.append("Tap a user below to view details.")
        lines.append("")
        for user in users:
            status = "Blocked" if user["is_blocked"] else "Active"
            lines.append(f"{get_display_name(user['first_name'], user['username'], user['user_id'])}")
            lines.append(f"ID: {user['user_id']} | Status: {status}")
            lines.append("")

    return "\n".join(lines).strip(), total_pages


def build_user_detail_text(user, rate_status, notice=None):
    """Format a single user's details."""
    lines = []
    if notice:
        lines.extend([notice, ""])

    lines.extend(
        [
            style_heading("User Details"),
            "",
            f"username: {format_username(user['username'])}",
            f"Name: {get_display_name(user['first_name'], user['username'], user['user_id'])}",
            f"ID: {user['user_id']}",
            f"Joined: {format_timestamp(user['created_at'])}",
            f"Last active: {format_timestamp(user['last_active'])}",
            f"Messages: {user['message_count']}",
            f"Status: {'Blocked' if user['is_blocked'] else 'Active'}",
            f"Rate usage: {rate_status['used_count']}/{rate_status['total_limit']} in {rate_status['window_hours']}h",
            f"Remaining now: {rate_status['remaining']}",
            f"Bonus quota: {rate_status['bonus_count']}",
            f"Active grants: {build_active_grants_summary(rate_status['active_grants'])}",
        ]
    )
    return "\n".join(lines)


async def send_dashboard_message(message, admin_user_id, edit=False):
    """Render dashboard as a reply or edited message."""
    dashboard_text = build_dashboard_text(admin_user_id)
    dashboard_keyboard = build_dashboard_keyboard()

    if edit:
        await safe_edit_text(message, dashboard_text, reply_markup=dashboard_keyboard)
    else:
        await message.reply_text(dashboard_text, reply_markup=dashboard_keyboard)


async def show_user_management(query, page):
    """Render paginated user management list."""
    page = max(0, page)
    users, total_users = db.get_users_page(
        page=page,
        page_size=USER_PAGE_SIZE,
        exclude_user_ids=ADMIN_IDS,
    )

    if page > 0 and not users:
        page = max(0, page - 1)
        users, total_users = db.get_users_page(
            page=page,
            page_size=USER_PAGE_SIZE,
            exclude_user_ids=ADMIN_IDS,
        )

    text, total_pages = build_user_list_text(users, page, total_users)
    keyboard = build_user_list_keyboard(users, page, total_pages)
    await safe_edit_text(query.message, text, reply_markup=keyboard)


async def show_user_details(query, user_id, page, notice=None):
    """Render a single user's detail view."""
    user = db.get_user_details(user_id)

    if not user or user_id in ADMIN_IDS:
        await safe_edit_text(
            query.message,
            "User not found.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Back to Users", callback_data=f"admin:users:{page}")],
                    [InlineKeyboardButton("Back to Dashboard", callback_data="admin:dashboard")],
                ]
            ),
        )
        return

    rate_status = db.get_user_rate_limit_status(user_id)
    text = build_user_detail_text(user, rate_status, notice=notice)
    keyboard = build_user_detail_keyboard(user_id, user["is_blocked"], page)
    await safe_edit_text(query.message, text, reply_markup=keyboard)


async def send_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, notification_text):
    """Broadcast a notification to all unblocked non-admin users."""
    admin_id = update.effective_user.id

    if len(notification_text) > 4096:
        await update.message.reply_text("Notification is too long. Telegram messages must be 4096 characters or less.")
        return

    excluded_ids = set(ADMIN_IDS)
    excluded_ids.add(admin_id)
    recipients = db.get_broadcast_recipients(exclude_user_ids=excluded_ids)
    blocked_users = db.get_blocked_user_count(exclude_user_ids=ADMIN_IDS)

    if not recipients:
        await update.message.reply_text("No available users to notify right now.")
        return

    progress_message = await update.message.reply_text("Sending notification to users...")

    success_count = 0
    failed_count = 0

    for user_id in recipients:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"Admin notification\n\n{notification_text}",
            )
            success_count += 1
        except Exception as exc:
            failed_count += 1
            print(f"[ERROR] Failed to send notification to {user_id}: {exc}")
        await asyncio.sleep(0.05)

    await safe_edit_text(
        progress_message,
        "\n".join(
            [
                "Notification sent.",
                f"Delivered: {success_count}",
                f"Failed: {failed_count}",
                f"Skipped blocked users: {blocked_users}",
            ]
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Dashboard", callback_data="admin:dashboard")]]
        ),
    )


async def process_admin_quota_grant(update: Update, quota_text):
    """Handle admin add-questions flow."""
    admin_id = update.effective_user.id

    try:
        user_id, extra_questions, hours = parse_quota_grant_text(quota_text)
    except ValueError as exc:
        await update.message.reply_text(
            f"{exc}\n\nExample: 12345-15-1",
            reply_markup=build_quota_grant_keyboard(),
        )
        return

    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            "Admin users already have unlimited access.",
            reply_markup=build_quota_grant_keyboard(),
        )
        return

    user = db.get_user_details(user_id)
    if not user:
        await update.message.reply_text(
            "User ID not found in the database.",
            reply_markup=build_quota_grant_keyboard(),
        )
        return

    success = db.grant_user_quota(
        user_id=user_id,
        extra_questions=extra_questions,
        hours=hours,
        granted_by=admin_id,
    )

    if not success:
        await update.message.reply_text(
            "Failed to add questions for this user.",
            reply_markup=build_quota_grant_keyboard(),
        )
        return

    clear_pending_admin_action(admin_id)
    rate_status = db.get_user_rate_limit_status(user_id)

    confirmation = "\n".join(
        [
            style_heading("Questions added successfully."),
            f"User: {get_display_name(user['first_name'], user['username'], user['user_id'])}",
            f"ID: {user_id}",
            f"Added questions: {extra_questions}",
            f"Duration: {hours} hour(s)",
            f"New total limit now: {rate_status['total_limit']}",
            f"Remaining now: {rate_status['remaining']}",
        ]
    )
    await update.message.reply_text(confirmation, reply_markup=build_dashboard_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_name = user.first_name or "Friend"

    register_user(user)

    if not is_admin(user_id) and db.is_user_blocked(user_id):
        await reply_blocked(update)
        return

    arrow = DECORATIONS["arrow"]
    lightning = DECORATIONS["lightning"]
    line = DECORATIONS["line_heavy"]
    skull = DECORATIONS["skull"]
    bracket_open = DECORATIONS["bracket_open"]
    bracket_close = DECORATIONS["bracket_close"]

    welcome_msg = f"""Bot Initialized for {user_name}

{line}
{arrow} Welcome to {style_markdown_text("HeaNg[Black-Cyber]")} {arrow}
{line}

{lightning} I am an intelligent AI assistant
{arrow} ready to answer your questions
{arrow} and provide detailed information.

{line}
{bracket_open} Features {bracket_close}
{arrow} AI-Powered Coding Assistance
{arrow} Pattern Recognition
{arrow} Conversation History (Use /history)
{arrow} Real-Time Solutions
{line}

Send your message to get started!
Use /history to view past conversations

Let's Explore {lightning} {skull}
{line}"""

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Developer", url="https://t.me/mengheang25")]]
    )

    try:
        image_path = "how-cybercriminals-are-using-genai-like-wormgpt-and-v0-ijdhl7mcrnte1.webp"
        with open(image_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome_msg,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
    except Exception:
        await update.message.reply_text(welcome_msg, parse_mode="Markdown", reply_markup=keyboard)


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command to show conversation history."""
    user = update.effective_user
    user_id = user.id
    register_user(user)

    if not is_admin(user_id) and db.is_user_blocked(user_id):
        await reply_blocked(update)
        return

    arrow = DECORATIONS["arrow"]
    lightning = DECORATIONS["lightning"]
    line = DECORATIONS["line_medium"]

    if not ENABLE_HISTORY:
        await update.message.reply_text(f"{arrow} Conversation History Is Disabled")
        return

    history = db.get_user_history(user_id, limit=20)

    if not history:
        await update.message.reply_text(f"{arrow} Your Conversation History Is Empty")
        return

    history_text = f"{lightning} Your Conversation History {lightning}\n{line}\n"

    for msg_type, content, timestamp in history:
        ts = format_timestamp(timestamp)

        if msg_type == "user":
            history_text += f"\nUser: [{ts}]\n{content}\n"
        else:
            history_text += f"\nAI: [{ts}]\n{content}\n"

        history_text += line + "\n"

    if len(history_text) > 4096:
        chunks = [history_text[i : i + 4096] for i in range(0, len(history_text), 4096)]
        for chunk in chunks:
            await update.message.reply_text(chunk)
    else:
        await update.message.reply_text(history_text)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clearhistory command to delete conversation history."""
    user = update.effective_user
    user_id = user.id
    register_user(user)

    if not is_admin(user_id) and db.is_user_blocked(user_id):
        await reply_blocked(update)
        return

    arrow = DECORATIONS["arrow"]
    skull = DECORATIONS["skull"]

    if not ENABLE_HISTORY:
        await update.message.reply_text(f"{arrow} Conversation History Is Disabled")
        return

    if db.clear_user_history(user_id):
        await update.message.reply_text(f"{skull} Your Conversation History Has Been Cleared")
    else:
        await update.message.reply_text(f"{arrow} No History To Clear")


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin dashboard command."""
    user = update.effective_user
    register_user(user)

    if not is_admin(user.id):
        await update.message.reply_text("This command is for admins only.")
        return

    clear_pending_admin_action(user.id)
    await send_dashboard_message(update.message, user.id, edit=False)


def format_code_snippets(text):
    """Format code snippets for Telegram HTML format."""
    import re

    pattern = r"```(?:\w+)?\n(.*?)```"

    def replace_code_block(match):
        code_content = match.group(1).strip()
        escaped_code = html.escape(code_content)
        return f"<pre>{escaped_code}</pre>"

    formatted_text = re.sub(pattern, replace_code_block, text, flags=re.DOTALL)

    inline_pattern = r"`([^`]+)`"
    formatted_text = re.sub(inline_pattern, r"<code>\1</code>", formatted_text)

    return formatted_text


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    text = update.message.text

    register_user(user)

    if is_admin(uid):
        admin_action = get_pending_admin_action(uid)
        if admin_action:
            if admin_action["type"] == "broadcast":
                clear_pending_admin_action(uid)
                await send_admin_broadcast(update, context, text)
                return
            if admin_action["type"] == "quota_grant":
                await process_admin_quota_grant(update, text)
                return

    if not is_admin(uid) and db.is_user_blocked(uid):
        await reply_blocked(update)
        return

    if not is_admin(uid):
        rate_status = db.get_user_rate_limit_status(uid)
        if rate_status["remaining"] <= 0:
            await update.message.reply_text(build_rate_limit_exceeded_text(rate_status))
            return

    user_last_messages[uid] = text
    model_messages = build_conversation_messages(uid, text)

    arrow = DECORATIONS["arrow"]
    lightning = DECORATIONS["lightning"]

    loading_msg = await update.message.reply_text(f"{lightning} Processing {arrow} HeaNg[Black-Cyber] core...")

    await update.message.chat.send_action("typing")
    await asyncio.sleep(1)

    try:
        reply = ask_model(model_messages)
    except RuntimeError as exc:
        await safe_edit_text(
            loading_msg,
            f"API request failed after retry.\n{exc}",
        )
        return

    if not is_admin(uid):
        db.record_rate_limit_event(uid)

    db.save_message(uid, "user", text)
    db.save_message(uid, "ai", reply)

    formatted_reply = format_code_snippets(reply)

    if len(formatted_reply) > 4096:
        chunks = [formatted_reply[i : i + 4096] for i in range(0, len(formatted_reply), 4096)]
        await safe_edit_text(loading_msg, chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await safe_edit_text(loading_msg, formatted_reply, parse_mode="HTML")


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    user = query.from_user
    register_user(user)

    if data.startswith("admin:"):
        if not is_admin(user.id):
            await query.answer("Admin only.", show_alert=True)
            return

        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        if action == "dashboard":
            clear_pending_admin_action(user.id)
            await query.answer()
            await send_dashboard_message(query.message, user.id, edit=True)
            return

        if action == "users":
            await query.answer()
            page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            await show_user_management(query, page)
            return

        if action == "user":
            if len(parts) < 4 or not parts[2].isdigit() or not parts[3].isdigit():
                await query.answer("Invalid user selection.", show_alert=True)
                return
            target_user_id = int(parts[2])
            page = int(parts[3])
            await query.answer()
            await show_user_details(query, target_user_id, page)
            return

        if action in {"block", "unblock"}:
            if len(parts) < 4 or not parts[2].isdigit() or not parts[3].isdigit():
                await query.answer("Invalid user action.", show_alert=True)
                return

            target_user_id = int(parts[2])
            page = int(parts[3])

            if target_user_id in ADMIN_IDS:
                await query.answer("You cannot block an admin.", show_alert=True)
                return

            updated = db.set_user_blocked(target_user_id, blocked=(action == "block"))
            if not updated:
                await query.answer("User not found.", show_alert=True)
                return

            notice = "User blocked successfully." if action == "block" else "User unblocked successfully."
            await query.answer()
            await show_user_details(query, target_user_id, page, notice=notice)
            return

        if action == "broadcast":
            subaction = parts[2] if len(parts) > 2 else ""
            if subaction == "start":
                set_pending_admin_action(user.id, "broadcast")
                await query.answer()
                await safe_edit_text(
                    query.message,
                    "Send the notification text now.\n\nYour next text message will be sent to all available users immediately.",
                    reply_markup=build_broadcast_keyboard(),
                )
                return

            if subaction == "cancel":
                clear_pending_admin_action(user.id)
                await query.answer()
                await send_dashboard_message(query.message, user.id, edit=True)
                return

        if action == "grant":
            subaction = parts[2] if len(parts) > 2 else ""
            if subaction == "start":
                set_pending_admin_action(user.id, "quota_grant")
                await query.answer()
                await safe_edit_text(
                    query.message,
                    "Send the quota in this format:\n\nuser_id-extra_questions-hours\n\nExample:\n12345-15-1",
                    reply_markup=build_quota_grant_keyboard(),
                )
                return

            if subaction == "cancel":
                clear_pending_admin_action(user.id)
                await query.answer()
                await send_dashboard_message(query.message, user.id, edit=True)
                return

        await query.answer()
        await safe_edit_text(
            query.message,
            "Unknown admin action.",
            reply_markup=build_dashboard_keyboard(),
        )
        return

    await query.answer()
    uid = user.id

    if not is_admin(uid) and db.is_user_blocked(uid):
        await reply_blocked(update)
        return

    arrow = DECORATIONS["arrow"]
    lightning = DECORATIONS["lightning"]

    if uid not in user_last_messages:
        await safe_edit_text(query.message, f"{arrow} No cached messages available now. {lightning}")
        return

    if not is_admin(uid):
        rate_status = db.get_user_rate_limit_status(uid)
        if rate_status["remaining"] <= 0:
            await safe_edit_text(query.message, build_rate_limit_exceeded_text(rate_status))
            return

    await safe_edit_text(query.message, f"{lightning} Processing {arrow} HeaNg[Black-Cyber] core...")
    await query.message.chat.send_action("typing")
    await asyncio.sleep(0.8)

    retry_prompt = user_last_messages[uid]
    retry_messages = build_conversation_messages(uid, retry_prompt)

    try:
        reply = ask_model(retry_messages)
    except RuntimeError as exc:
        await safe_edit_text(query.message, f"API request failed after retry.\n{exc}")
        return

    if not is_admin(uid):
        db.record_rate_limit_event(uid)

    db.save_message(uid, "ai", reply)

    formatted_reply = format_code_snippets(reply)

    if len(formatted_reply) > 4096:
        chunks = [formatted_reply[i : i + 4096] for i in range(0, len(formatted_reply), 4096)]
        await safe_edit_text(query.message, chunks[0], parse_mode="HTML")
        for chunk in chunks[1:]:
            await query.message.reply_text(chunk, parse_mode="HTML")
    else:
        await safe_edit_text(query.message, formatted_reply, parse_mode="HTML")


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


async def error_handler(update, context):
    """Log the error and send a message to the user."""
    arrow = DECORATIONS["arrow"]
    skull = DECORATIONS["skull"]

    print(f"[ERROR] Update {update} caused error {context.error}")

    error_msg = f"{skull} Oops! {arrow} Something went wrong.\nPlease try again later."

    if update and getattr(update, "message", None):
        try:
            await update.message.reply_text(error_msg)
        except Exception:
            pass
    elif update and getattr(update, "callback_query", None):
        try:
            await update.callback_query.message.reply_text(error_msg)
        except Exception:
            pass


app.add_error_handler(error_handler)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("history", show_history))
app.add_handler(CommandHandler("clearhistory", clear_history))
app.add_handler(CommandHandler(["dashboard", "dashoard"], dashboard))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(callback))

line = DECORATIONS["line_heavy"]
arrow = DECORATIONS["arrow"]
lightning = DECORATIONS["lightning"]
skull = DECORATIONS["skull"]

startup_msg = f"""
{line}
{arrow} Bot is now active {arrow}
{lightning} Time: {time.strftime("%H:%M:%S")}
{skull} Running on Render.com {skull}
{line}
"""

print(startup_msg)

# Python 3.14+ requires explicit event loop initialization
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

app.run_polling()
