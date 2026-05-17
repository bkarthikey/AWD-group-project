"""
Set a new password for an account by email (local / dev helper).

Run from the project folder (where `app` and `run.py` live):

  python scripts/reset_password.py "your@email.com" "YourNewPassword8+"

Password must be at least 8 characters (same rule as signup).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User  # noqa: E402


def main():
    if len(sys.argv) != 3:
        print('Usage: python scripts/reset_password.py "you@email.com" "NewPasswordAtLeast8Chars"')
        sys.exit(1)
    email = sys.argv[1].strip().lower()
    new_pw = sys.argv[2]

    if len(new_pw) < 8:
        print("Error: password must be at least 8 characters.")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"No account found with email: {email}")
            sys.exit(1)
        user.set_password(new_pw)
        db.session.commit()
        print("Done.")
        print(f"  Commander: {user.username}")
        print(f"  Email:     {email}")
        print("Log in at /login with that email and the new password you just set.")


if __name__ == "__main__":
    main()
