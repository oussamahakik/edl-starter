from enum import Enum
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from .database import Base

# =============================================================================
# ENUMS (Statut et Priorité)
# =============================================================================

class TaskStatus(str, Enum):
    """Statuts possibles d'une tâche."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class TaskPriority(str, Enum):
    """Priorités possibles d'une tâche."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# =============================================================================
# MODÈLE ORM
# =============================================================================

class TaskModel (Base):
    """Modèle SQLAlchemy pour la table tasks."""
    __tablename__ = "tasks" # Nom de la table dans la base de données

    # L'ID est maintenant un String (UUID) pour la compatibilité avec PostgreSQL
    id = Column(String, primary_key=True, index=True)
    
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Utilisation du type SQLEnum pour garantir la validité des valeurs
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(SQLEnum (TaskPriority), default=TaskPriority.MEDIUM)
    
    assignee = Column(String(100), nullable=True)
    due_date = Column (DateTime, nullable=True)
    
    # Timestamps gérés automatiquement par la base de données (server_default)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())