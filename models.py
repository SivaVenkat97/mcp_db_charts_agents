from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

# Tables
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)

    conversations = relationship("Conversation", back_populates="session", cascade="all, delete")
    assets = relationship("Asset", back_populates="session", cascade="all, delete")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=True)
    response = Column(String, nullable=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)

    session = relationship("ChatSession", back_populates="conversations")
    assets = relationship("Asset", back_populates="conversation", cascade="all, delete")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    path = Column(String, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    aspect_ratio = Column(Float, nullable=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    query = Column(String, nullable=True)
    chart_data = Column(String, nullable=True)
    chart_type = Column(String, nullable=True)

    session = relationship("ChatSession", back_populates="assets")
    conversation = relationship("Conversation", back_populates="assets")
    dashboards = relationship("DashboardAsset", back_populates="asset", cascade="all, delete")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)

    assets = relationship("DashboardAsset", back_populates="dashboard", cascade="all, delete")


class DashboardAsset(Base):
    __tablename__ = "dashboard_assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=False)

    asset = relationship("Asset", back_populates="dashboards")
    dashboard = relationship("Dashboard", back_populates="assets")



# Create DB
engine = create_engine("sqlite:///chat_app.db", echo=True)
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()

# Insert sample data
chat_session = ChatSession()
session.add(chat_session)
session.commit()

conversation = Conversation(question="What is AI?", response="AI is Artificial Intelligence", session_id=chat_session.id)
session.add(conversation)
session.commit()

asset = Asset(title="AI Diagram", path="/assets/ai_diagram.png", width=800, height=600,
              aspect_ratio=800/600, session_id=chat_session.id, conversation_id=conversation.id)
session.add(asset)
session.commit()

dashboard = Dashboard(title="AI Dashboard")
session.add(dashboard)
session.commit()

dashboard_asset = DashboardAsset(asset_id=asset.id, dashboard_id=dashboard.id)
session.add(dashboard_asset)
session.commit()

print("All entries created successfully!")
