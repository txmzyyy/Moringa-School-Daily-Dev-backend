from models.user import User
from extensions import db

def register_user(first_name, last_name, email, password, role=None):
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        raise ValueError("Email already registered")

    if role not in ("user", "writer"):
     role = "user"
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        role=role
    )

    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return user

def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if not user:
        return None
    if not user.is_active:
        return None
    if not user.check_password(password):
        return None

    return user