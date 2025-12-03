import pytest
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database import Base, get_db
from src.models import TaskModel
from fastapi.testclient import TestClient
from src.app import app


# =============================================================================
# Configuration de la base de test SQLite temporaire (Exercice 5)
# =============================================================================

TEST_DB_FILE = tempfile.mktemp(suffix=".db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Utilisé pour garantir un thread unique par test
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def setup_test_database():
    """Crée/détruit les tables une seule fois pour la session de tests."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(autouse=True)
def clear_test_data(setup_test_database):
    """Nettoie les données (DELETE FROM) entre chaque test."""
    # S'assure que chaque test commence avec une base vide
    db = TestSessionLocal()
    db.query(TaskModel).delete()
    db.commit()
    db.close()
    yield # Le yield ici permet de marquer le point de setup, mais le nettoyage est fait avant.

@pytest.fixture
def client(setup_test_database):
    """Client de test FastAPI qui surcharge get_db pour utiliser la base de test."""
    
    # Fonction qui remplace get_db pour utiliser la base de test
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # Surcharge la dépendance de production par la dépendance de test
    app.dependency_overrides[get_db] = override_get_db
    
    # Exécute le client de test
    with TestClient(app) as c:
        yield c
        
    # Nettoie la surcharge après tous les tests de la session
    app.dependency_overrides.clear()


def pytest_configure(config):
    """Enregistre les markers personnalisés."""
    config.addinivalue_line(
    "markers",
    "e2e: mark test as end-to-end test (slow)"
    )