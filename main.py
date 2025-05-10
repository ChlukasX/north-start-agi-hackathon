import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict
from agent_factory import AgentFactory
from pydantic import BaseModel
from utils import PostgresDB

try:
    from utils.database_connection import PostgresDB
except ImportError:
    # This fallback is just for development ease if the file is missing,
    # but in production, this should not happen.
    raise ImportError(
        "database_connection.py not found. Please ensure it exists with the PostgresDB class."
    )

# Database configuration (matches your docker-compose)
DB_CONFIG = {
    "host": "localhost",  # This should be 'postgres' if FastAPI runs in the same Docker network
    # or the host IP if FastAPI runs outside Docker accessing the mapped port.
    # For local development with port mapping 5433:5432, 'localhost' and port 5433 is correct.
    "port": "5433",
    "user": "devuser",
    "password": "devpassword",
    "dbname": "devdb",
}

# Global instance of the database manager
# This instance will persist across requests as long as the FastAPI app is running.
db = PostgresDB(
    dbname=DB_CONFIG["dbname"],
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"],
    host=DB_CONFIG["host"],
    port=DB_CONFIG["port"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if db.connect():
        print("Application startup: attempting to connect to the database...")
    yield
    db.disconnect()


app = FastAPI(
    lifespan=lifespan,
    title="PostgreSQL Interaction API",
    description="API to connect, disconnect, and query a PostgreSQL database.",
    version="1.0.0",
)


# Dependency to get the DB instance and ensure it's connected for operations
def get_database_instance():
    if not db.is_connected:  # Using the property from PostgresDB class
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail="Database is not connected. Please use the POST /connect endpoint first.",
        )
    return db


@app.post("/connect", tags=["Connection Management"], summary="Connect to the database")
async def connect_to_db() -> Dict[str, str]:
    """
    Establishes a connection to the PostgreSQL database.
    """
    if db.is_connected:
        return {"status": "success", "message": "Already connected to the database."}
    if db.connect():
        return {
            "status": "success",
            "message": "Successfully connected to the database.",
        }
    else:
        # The error message from db.connect() is printed to console.
        # We can provide a more generic message here or try to capture specific error.
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to the database. Check server logs for details.",
        )


@app.post(
    "/disconnect",
    tags=["Connection Management"],
    summary="Disconnect from the database",
)
async def disconnect_from_db() -> Dict[str, str]:
    """
    Closes the connection to the PostgreSQL database.
    """
    if not db.is_connected:
        return {
            "status": "success",
            "message": "Already disconnected from the database.",
        }
    if (
        db.disconnect()
    ):  # disconnect should ideally always return True or handle its errors.
        return {
            "status": "success",
            "message": "Successfully disconnected from the database.",
        }
    else:
        # This path might be less common if db.disconnect() is robust
        raise HTTPException(
            status_code=500,
            detail="An error occurred during disconnection. Check server logs.",
        )


@app.get(
    "/status",
    tags=["Connection Management"],
    summary="Check database connection status",
)
async def get_connection_status() -> Dict[str, str]:
    """
    Checks and returns the current connection status to the database.
    """
    if db.is_connected:
        return {"status": "connected", "message": "Database is currently connected."}
    else:
        return {"status": "disconnected", "message": "Database is not connected."}


@app.get(
    "/tables",
    response_model=List[str],
    tags=["Database Operations"],
    summary="Get all table names",
)
async def get_all_tables(db_instance: PostgresDB = Depends(get_database_instance)):
    """
    Retrieves a list of all user-defined tables in the connected database.
    Requires an active database connection.
    """
    tables = db_instance.get_all_tables()
    # get_all_tables returns [] on error or if not connected,
    # but the dependency `get_database_instance` should catch "not connected".
    return tables


@app.get(
    "/tables/{table_name}/columns",
    response_model=List[str],
    tags=["Database Operations"],
    summary="Get all columns for a table",
)
async def get_all_columns(
    table_name: str, db_instance: PostgresDB = Depends(get_database_instance)
):
    """
    Retrieves a list of all column names for a specified table.
    Requires an active database connection.
    """
    if not table_name.strip():
        raise HTTPException(status_code=400, detail="Table name cannot be empty.")

    columns = db_instance.get_table_columns(table_name)
    if (
        not columns and table_name not in db_instance.get_all_tables()
    ):  # Additional check if columns list is empty
        # This check helps differentiate an empty table/no columns from a non-existent table.
        # Note: db_instance.get_table_columns itself already prints if table doesn't exist.
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found.")
    return columns


agent_instances = {}


class QueryRequest(BaseModel):
    agent_type: str
    query: str


async def get_agent(agent_type: str):
    if agent_type not in agent_instances:
        try:
            agent_instances[agent_type] = AgentFactory.create_agent(agent_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return agent_instances[agent_type]


@app.post("/query")
async def process_query(
    db_instance: PostgresDB = Depends(get_database_instance),
    request=QueryRequest,
    agent=Depends(get_agent),
):
    try:
        response = await asyncio.to_thread(agent.llm, request.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "message": "Agent API is running. Use /query endpoint to interact with agents."
    }


# You can then access the API endpoints:
# - POST http://localhost:8000/connect
# - POST http://localhost:8000/disconnect
# - GET  http://localhost:8000/status
# - GET  http://localhost:8000/tables
# - GET  http://localhost:8000/tables/your_table_name/columns
