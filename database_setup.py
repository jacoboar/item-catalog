import datetime
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy import String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


def get_current_time():
    return datetime.datetime.now()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    user = relationship("Team", cascade='delete')

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Country(Base):
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    date = Column(DateTime, default=get_current_time,
                  onupdate=get_current_time)

    def __init__(self, name):
        self.name = name

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id
        }


class Team(Base):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(250), nullable=False)
    country_id = Column(Integer, ForeignKey('country.id'))
    country = relationship(Country)
    date = Column(DateTime, default=get_current_time,
                  onupdate=get_current_time)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    def __init__(self, name, description, country_id, user_id):
        self.name = name
        self.description = description
        self.country_id = country_id
        self.user_id = user_id

    @property
    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'country_id': self.country_id,
            'user_id': self.user_id
        }


engine = create_engine('sqlite:///catalog.db')

Base.metadata.bind = engine
Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
