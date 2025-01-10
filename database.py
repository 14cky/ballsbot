# database.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import create_engine, Index

Base = declarative_base()

class Group(Base):
    __tablename__ = 'groups'
    group_id = Column(Integer, primary_key=True)
    group_name = Column(String)
    users = relationship("User", back_populates="group")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String)
    total_sum = Column(Float, default=0.0)
    last_random = Column(DateTime)
    group_id = Column(Integer, ForeignKey('groups.group_id'))
    group = relationship("Group", back_populates="users")
    
    __table_args__ = (
        Index('idx_user_group', 'user_id', 'group_id'),
    )

engine = create_engine('sqlite:///users.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
