from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine("postgresql://neondb_owner:npg_TdVPw4JbyB8A@ep-orange-pine-a4d5ngsg-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require", echo=True)
# engine = create_engine("mysql+mysqlconnector://root:admin@localhost:3306/python_db", echo=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



