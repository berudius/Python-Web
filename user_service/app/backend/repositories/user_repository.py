from sqlalchemy.orm import Session
from ..models.User import User
from passlib.context import CryptContext
from typing import List, Dict, Optional, Any

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_all_users(db: Session) -> List[User]:
    return db.query(User).all()

def get_user_by_login(db: Session, login: str):
    return db.query(User).filter(User.login == login).first()

def get_user_by_id(db: Session, id: int):
    return db.query(User).filter(User.id == id).first()

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def authenticate_user(db: Session, login: str, password: str):
    user = get_user_by_login(db, login)
    if not user:
        return None
    if not verify_password(password, user.hash_password):
        return None
    return user

def create_user(db: Session, login: str, password: str):
    
    hashed = pwd_context.hash(password)
    user = User(login = login, hash_password = hashed, role = "user")
    db.add(user)
    db.commit()
    db.refresh(user)

def update_user(db: Session, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    
    if user:
        # Динамічно оновлюємо поля
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
    
    return user

