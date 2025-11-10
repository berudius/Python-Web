from sqlalchemy import Column, Integer, String
from common.db.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(32), unique=True, nullable=False)
    role = Column(String(20), nullable=False)
    hash_password = Column(String(60), nullable=False)
    email = Column(String(254), unique=True, nullable=True)
    phone_number = Column(String(50), unique=True, nullable=True)
    trust_level = Column(Integer, default=0) 

        
    