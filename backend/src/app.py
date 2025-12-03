"""
TaskFlow Backend - FastAPI Task Management Service

A RESTful API for task management with TDD approach.

TP 1 & 2: Uses in-memory storage for simplicity
TP 3: Will introduce PostgreSQL database (see migration guide)
"""
from contextlib import asynccontextmanager
import uuid 
from fastapi import Depends 
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import get_db, init_db 
from .models import TaskModel, TaskStatus, TaskPriority # Utilise les modèles DB
from fastapi.middleware.cors import CORSMiddleware
import os

from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("taskflow")


# =============================================================================
# ENUMS & MODELS
# =============================================================================
# X SUPPRIMER: Les Enums TaskStatus et TaskPriority sont maintenant importées de .models

class TaskCreate(BaseModel):
    """Model for creating a new task."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    # Utilise TaskStatus importé de .models
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task status") 
    # Utilise TaskPriority importé de .models
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority") 
    assignee: Optional[str] = Field(None, max_length=100, description="Assigned user")
    due_date: Optional[datetime] = Field(None, description="Due date")


class TaskUpdate(BaseModel):
    """Model for updating a task - all fields optional for partial updates."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = None


# APRÈS (compatible SQLAlchemy)
class Task(BaseModel): 
    """Model for task response."""
    id: str # Changé en str pour UUID
    title: str 
    description: Optional[str] = None 
    status: TaskStatus 
    priority: TaskPriority
    assignee: Optional[str] = None 
    due_date: Optional[datetime] = None 
    created_at: datetime 
    updated_at: datetime

    class Config:
        from_attributes = True # Permet la conversion depuis SQLAlchemy


@asynccontextmanager 
async def lifespan(app: FastAPI): 
    """Lifecycle manager initialise la DB au démarrage."""
    logger.info("🚀 TaskFlow backend starting up...")
    init_db() # Crée les tables
    logger.info("Database initialized") 
    yield 
    logger.info("🛑 TaskFlow backend shutting down...") 

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="TaskFlow API",
    description="Simple task management API for learning unit testing and CI/CD",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan, # ← Ajout du manager de cycle de vie
)

# Configuration CORS pour le frontend
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173, http://127.0.0.1:5173") 
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Welcome to TaskFlow API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)): # Injection de Session DB
    """Health check with database status."""
    try:
        # Vérifie la connexion
        db.execute(text("SELECT 1"))
        tasks_count = db.query(TaskModel).count()
        return {
            "status": "healthy",
            "database": "connected",
            "tasks_count": tasks_count
        }
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


# X SUPPRIMER LE PREMIER ENDPOINT GET /tasks ICI X
# Le second endpoint, correct, est conservé ci-dessous.


@app.get("/tasks", response_model=List[Task])
async def get_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee: Optional[str] = None,
    db: Session = Depends(get_db) # Injection de Session DB
) -> List[Task]:
    """Get all tasks with optional filtering."""
    
    query = db.query(TaskModel) # Démarrer la requête sur le modèle DB
    
    # Appliquer les filtres SQLAlchemy
    if status:
        query = query.filter(TaskModel.status == status)
    if priority:
        query = query.filter(TaskModel.priority == priority)
    if assignee:
        query = query.filter(TaskModel.assignee == assignee)

    return query.all() # Exécuter la requête et retourner les résultats

@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, db: Session = Depends(get_db)) -> Task:
    """Get a single task by ID."""
    
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
    return task


@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)) -> Task:
    """Create a new task."""
    
    # 1. Validation 
    if not task_data.title or not task_data.title.strip():
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    # 2. Créer un TaskModel avec un UUID
    task = TaskModel(
        id=str(uuid.uuid4()), # Utilise UUID pour l'ID
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assignee=task_data.assignee,
        due_date=task_data.due_date,
    )

    # 3. Ajouter à la session, commiter, et rafraîchir
    db.add(task)
    db.commit()
    db.refresh(task) # Recharge l'objet pour obtenir les timestamps

    logger.info(f"Task created successfully: {task.id}")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, updates: TaskUpdate, db: Session = Depends(get_db)) -> Task:
    """Update an existing task (partial update supported)."""
    
    # 1. Trouver la tâche
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
    # 2. Extraire les champs à mettre à jour
    update_data = updates.model_dump(exclude_unset=True)

    # 3. Validation du titre (si fourni)
    if "title" in update_data and (not update_data["title"] or not update_data["title"].strip()):
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    # 4. Appliquer les mises à jour
    for key, value in update_data.items():
        setattr(task, key, value) # Utilise setattr pour la mise à jour des champs
    
    # 5. Commiter et rafraîchir
    db.commit()
    db.refresh(task) # Recharge pour mettre à jour 'updated_at'
    
    return task


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete a task by ID."""
    
    # 1. Trouver la tâche
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
    # 2. Supprimer la tâche et commiter
    db.delete(task)
    db.commit()
    
    return # Retourne 204 No Content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)