"""
Database Connection & Session Management
SQLAlchemy setup and session factory
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging
from datetime import datetime
from typing import Any, Dict, Optional

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
    
    # Import additional models to ensure tables are created
    try:
        import life_direction.models  # noqa: F401
    except ImportError:
        logger.warning("Life direction models not found during database initialization")

    try:
        import database.auth_models  # noqa: F401
    except ImportError:
        logger.warning("Auth models not found during database initialization")
    
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


def upsert_device_record(
    device_id: str,
    device_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    is_active: bool = True,
) -> None:
    """Create or refresh a device record for discovery results."""
    from database.models import DeviceRecord

    session = get_db_session()
    try:
        record = session.query(DeviceRecord).filter(DeviceRecord.id == device_id).first()
        if record is None:
            record = DeviceRecord(id=device_id, device_type=device_type)
            session.add(record)

        record.device_type = device_type
        record.is_active = is_active
        record.last_seen = datetime.utcnow()
        record.metadata_json = metadata or {}
        session.commit()
    finally:
        session.close()


def update_device_state(
    device_id: str,
    *,
    is_connected: bool,
    is_locked: bool,
    battery_level: Optional[int] = None,
    foreground_app: Optional[str] = None,
    installed_apps: Optional[Dict[str, Any] | list] = None,
    screenshot_uri: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist the latest observed device state."""
    from database.models import DeviceState

    session = get_db_session()
    try:
        state = DeviceState(
            device_id=device_id,
            is_connected=is_connected,
            is_locked=is_locked,
            battery_level=battery_level,
            foreground_app=foreground_app,
            installed_apps=installed_apps or {},
            permissions_cache=metadata or {},
            screenshot_uri=screenshot_uri,
            detected_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        session.add(state)
        session.commit()
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
