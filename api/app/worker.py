import os
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError

from .db import SessionLocal
from .emailer import send_email_smtp

print("[worker] DATABASE_URL=", os.environ.get("DATABASE_URL"))

POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "30"))
MAX_ATTEMPTS = int(os.getenv("WORKER_MAX_ATTEMPTS", "5"))

# 每隔多少秒打印一次指纹，避免刷屏
FP_EVERY_SECONDS = int(os.getenv("WORKER_FP_EVERY_SECONDS", "60"))
_last_fp_ts = 0.0

# DB 未就绪时的重试间隔
DB_READY_POLL_SECONDS = int(os.getenv("WORKER_DB_READY_POLL_SECONDS", "2"))


def _regclass(db: Session, name: str):
    return db.execute(text("select to_regclass(:n)"), {"n": name}).scalar_one()


def is_db_ready(db: Session) -> bool:
    letters = _regclass(db, "public.letters")
    users = _regclass(db, "public.users")
    return bool(letters) and bool(users)


def wait_for_db_ready():
    """
    在 worker 启动时等待 migrations / init 完成，避免 relation does not exist 刷屏。
    """
    print("[worker] waiting for db tables (public.letters, public.users)...")
    while True:
        db = SessionLocal()
        try:
            db.begin()
            ok = is_db_ready(db)
            # 顺带打一次指纹，方便你排查连到哪里
            log_db_fingerprint(db, force=True)
            db.commit()
            if ok:
                print("[worker] db ready ✅")
                return
            print(f"[worker] db not ready yet, sleep={DB_READY_POLL_SECONDS}s")
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[worker] db-ready check error: {type(e).__name__}: {e} sleep={DB_READY_POLL_SECONDS}s")
        finally:
            db.close()
        time.sleep(DB_READY_POLL_SECONDS)


def log_db_fingerprint(db: Session, force: bool = False):
    global _last_fp_ts
    now_ts = time.time()
    if (not force) and (now_ts - _last_fp_ts < FP_EVERY_SECONDS):
        return
    _last_fp_ts = now_ts

    fp = db.execute(
        text("""
            select
              inet_server_addr()::text as addr,
              inet_server_port() as port,
              current_database() as db,
              current_schema() as schema,
              current_setting('search_path') as search_path
        """)
    ).mappings().one()

    letters = _regclass(db, "public.letters")
    users = _regclass(db, "public.users")

    print("[worker] db_fingerprint=", dict(fp), "letters=", letters, "users=", users)


def fetch_one_due_letter(db: Session):
    """
    用 FOR UPDATE SKIP LOCKED 防止多个 worker 重复发送同一封信
    """
    row = db.execute(
        text("""
            SELECT id, user_id, subject, body
            FROM letters
            WHERE status = 'Scheduled'
              AND send_at_utc <= :now
              AND attempt_count < :max_attempts
            ORDER BY send_at_utc ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        """),
        {"now": datetime.now(timezone.utc), "max_attempts": MAX_ATTEMPTS},
    ).mappings().first()
    return row


def get_user_email(db: Session, user_id: str) -> str:
    row = db.execute(
        text("SELECT email FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).mappings().first()
    return row["email"] if row else ""


def mark_attempt(db: Session, letter_id: str):
    db.execute(
        text("UPDATE letters SET attempt_count = attempt_count + 1 WHERE id = :id"),
        {"id": letter_id},
    )


def mark_sent(db: Session, letter_id: str, provider_resp: str):
    # 你目前 schema 里没有 provider_resp 字段的话就先不写；先把状态/时间更新对
    db.execute(
        text("""
            UPDATE letters
            SET status='Sent',
                sent_at_utc=:sent_at,
                last_error=NULL
            WHERE id=:id
        """),
        {"id": letter_id, "sent_at": datetime.now(timezone.utc)},
    )


def mark_failed(db: Session, letter_id: str, err: str):
    db.execute(
        text("""
            UPDATE letters
            SET status='Failed',
                last_error=:err
            WHERE id=:id
        """),
        {"id": letter_id, "err": (err or "")[:4000]},
    )


def _looks_like_undefined_table(e: Exception) -> bool:
    # 兼容 sqlalchemy + psycopg 报错文本
    msg = str(e).lower()
    return ("undefinedtable" in msg) or ("relation" in msg and "does not exist" in msg)


def main():
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    smtp_from = os.environ["SMTP_FROM"]

    print(f"[worker] started poll={POLL_SECONDS}s max_attempts={MAX_ATTEMPTS}")

    # ✅ 启动先等 DB 表 ready
    wait_for_db_ready()

    while True:
        db = SessionLocal()
        try:
            db.begin()

            # ✅ 每隔一段时间打印一次：连到哪台 Postgres、哪个库、search_path、letters/users 是否存在
            log_db_fingerprint(db)

            job = fetch_one_due_letter(db)
            if not job:
                db.commit()
                time.sleep(POLL_SECONDS)
                continue

            letter_id = str(job["id"])
            user_id = str(job["user_id"])
            subject = job["subject"]
            body = job["body"]

            mark_attempt(db, letter_id)

            mail_to = get_user_email(db, user_id)
            if not mail_to:
                mark_failed(db, letter_id, "User email not found")
                db.commit()
                continue

            ok, resp = send_email_smtp(
                host=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_pass,
                mail_from=smtp_from,
                mail_to=mail_to,
                subject=subject,
                body=body,
            )

            if ok:
                print(f"[worker] SENT letter_id={letter_id} to={mail_to} resp={resp}")
                mark_sent(db, letter_id, resp)
            else:
                print(f"[worker] FAIL letter_id={letter_id} to={mail_to} err={resp}")
                mark_failed(db, letter_id, resp)

            db.commit()

        except Exception as e:
            # ✅ 出错时强制打印一次指纹
            try:
                log_db_fingerprint(db, force=True)
            except Exception:
                pass

            try:
                db.rollback()
            except Exception:
                pass

            # ✅ 如果是表不存在：回到 wait 模式，不要刷屏
            if _looks_like_undefined_table(e):
                print(f"[worker] tables missing (UndefinedTable). back to wait_for_db_ready(). err={type(e).__name__}: {e}")
                wait_for_db_ready()
                continue

            print(f"[worker] loop error: {type(e).__name__}: {e}")
            time.sleep(POLL_SECONDS)

        finally:
            db.close()


if __name__ == "__main__":
    main()
