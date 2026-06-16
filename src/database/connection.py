"""
Database Connection & Session Management
SQLAlchemy setup and session factory
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging

from config import Config
from database.models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
engine = None
SessionLocal = None


def init_database():
    """Initialize database connection and create tables"""
    global engine, SessionLocal
    
    config = Config.get_database_config()
    
    logger.info(f"Connecting to database: {config.host}:{config.port}/{config.database}")
    
    # Create engine
    engine = create_engine(
        config.connection_string,
        poolclass=QueuePool,
        pool_size=config.pool_size,
        echo=Config.DEBUG,
        connect_args={"connect_timeout": 10},
    )
    
    # Create session factory
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    
    # Import life direction models lazily to avoid circular imports
    try:
        import life_direction.models  # noqa: F401
    except ImportError:
        logger.warning("Life direction models not found during database initialization")
    
    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database initialized successfully")


def get_db_session() -> Session:
    """Get database session"""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return SessionLocal()


def close_database():
    """Close database connections"""
    global engine
    if engine:
        engine.dispose()
        logger.info("Database connections closed")


async def create_workflow(
    user_id: str,
    command: str,
    intent: str,
    device_id: str,
    plan_json: dict = None,
    workflow_id: str | None = None,
) -> str:
    """
    Create a new workflow record
    
    Returns:
        Workflow ID
    """
    from database.models import Workflow, WorkflowStatus
    import uuid
    from datetime import datetime
    
    session = get_db_session()
    try:
        workflow_id = workflow_id or str(uuid.uuid4())
        
        workflow = Workflow(
            id=workflow_id,
            user_id=user_id,
            command=command,
            intent=intent,
            status=WorkflowStatus.PENDING,
            device_id=device_id,
            plan_json=plan_json,
            created_at=datetime.utcnow(),
        )
        
        session.add(workflow)
        session.commit()
        
        logger.info(f"Created workflow: {workflow_id}")
        
        return workflow_id
    finally:
        session.close()


def get_workflow(workflow_id: str):
    """Get workflow by ID"""
    from database.models import Workflow
    
    session = get_db_session()
    try:
        return session.query(Workflow).filter(Workflow.id == workflow_id).first()
    finally:
        session.close()


def update_workflow(workflow_id: str, **kwargs):
    """Update workflow status/fields"""
    from database.models import Workflow
    from datetime import datetime
    
    session = get_db_session()
    try:
        workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
        
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        for key, value in kwargs.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        
        workflow.updated_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Updated workflow: {workflow_id}")
    finally:
        session.close()


# Async context managers for transaction handling
class AsyncTransaction:
    """Async transaction context manager"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = get_db_session()
        return self.session
    
    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            self.session.rollback()
            logger.error(f"Transaction rolled back due to exception: {exc}")
        else:
            self.session.commit()
        
        self.session.close()


async def with_transaction(func, *args, **kwargs):
    """Execute async function within transaction"""
    async with AsyncTransaction() as session:
        return await func(session, *args, **kwargs)
