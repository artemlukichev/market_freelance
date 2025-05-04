from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy_schemadisplay import create_schema_graph
from sqlalchemy import Column, Integer, String, ForeignKey

DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)

graph = create_schema_graph(
    metadata=Base.metadata,
    engine=engine,
    show_datatypes=True,
    show_indexes=False,
)

graph.write_png('er_diagram.png')
