from sqlalchemy import text
import database.connection as db

db.init_database()

with db.SessionLocal() as s:
    result = s.execute(
        text("SELECT email, token, expires_at, used FROM email_verification_tokens ORDER BY created_at DESC LIMIT 5")
    )
    rows = result.fetchall()
    print(f"Verification tokens ({len(rows)}):")
    for r in rows:
        print(f"  {r[0]} | token={str(r[1])[:20]}... | expires={r[2]} | used={r[3]}")

    result = s.execute(
        text("SELECT id, email, email_verified, name FROM users ORDER BY created_at DESC LIMIT 5")
    )
    rows = result.fetchall()
    print(f"\nUsers ({len(rows)}):")
    for r in rows:
        print(f"  {r[0]} | {r[1]} | verified={r[2]} | name={r[3]}")
