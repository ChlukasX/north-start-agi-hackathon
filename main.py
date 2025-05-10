import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict
from agent_factory import AgentFactory
from pydantic import BaseModel
from enviroment_setup import setup_environment

# Set up environment variables and configuration
config = setup_environment()

# Configure logging
logger = logging.getLogger(__name__)

try:
    from utils.database_connection import PostgresDB
except ImportError:
    # This fallback is just for development ease if the file is missing,
    # but in production, this should not happen.
    raise ImportError(
        "database_connection.py not found. Please ensure it exists with the PostgresDB class."
    )

# Use environment variables for database configuration
DB_CONFIG = config["db_config"]

# Global instance of the database manager
db = PostgresDB(
    dbname=DB_CONFIG["dbname"],
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"],
    host=DB_CONFIG["host"],
    port=DB_CONFIG["port"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log API key status
    if config["openai_api_key"]:
        logger.info("OpenAI API key is configured")
    else:
        logger.warning(
            "OpenAI API key is not configured. OpenAI-based agents will not work."
        )

    if config["google_api_key"]:
        logger.info("Google API key is configured")
    else:
        logger.warning(
            "Google API key is not configured. Google-based agents will not work."
        )

    # Connect to database
    if db.connect():
        logger.info("Application startup: Successfully connected to the database")
    else:
        logger.error("Application startup: Failed to connect to the database")

    yield

    # Disconnect from database
    db.disconnect()
    logger.info("Application shutdown: Disconnected from the database")


app = FastAPI(
    lifespan=lifespan,
    title="Agent API",
    description="API to connect with agents and query a PostgreSQL database.",
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


# Agent management cache
agent_instances = {}


class QueryRequest(BaseModel):
    agent_type: str
    query: str


@app.post("/query", tags=["Agent Operations"], summary="Process a query using an agent")
async def process_query(request: QueryRequest):
    """
    Processes a query using the specified agent type.
    """
    try:
        # Validate API keys based on agent type
        if request.agent_type.lower() == "example" and not config["openai_api_key"]:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key not configured. This agent requires an OpenAI API key.",
            )
        elif (
            request.agent_type.lower() == "data access" and not config["google_api_key"]
        ):
            raise HTTPException(
                status_code=400,
                detail="Google API key not configured. This agent requires a Google API key.",
            )

        # Get or create the agent instance
        if request.agent_type not in agent_instances:
            try:
                agent_instances[request.agent_type] = AgentFactory.create_agent(
                    request.agent_type
                )
                logger.info(f"Created new agent instance of type: {request.agent_type}")
            except ValueError as e:
                logger.error(f"Invalid agent type requested: {request.agent_type}")
                raise HTTPException(status_code=400, detail=str(e))

        agent = agent_instances[request.agent_type]

        # Process the query with the agent
        logger.info(
            f"Processing query with {request.agent_type} agent: {request.query}"
        )
        response = []
        try:
            for step in agent.llm(request.query):
                if "messages" in step and len(step["messages"]) > 0:
                    response.append(step["messages"][-1].content)
                    logger.debug(
                        f"Agent response step: {step['messages'][-1].content[:50]}..."
                    )
        except Exception as e:
            logger.error(f"Error during agent processing: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error during agent processing: {str(e)}"
            )

        # Return the final response
        final_response = response[-1] if response else "No response generated"
        logger.info(
            f"Query processed successfully, response length: {len(final_response)}"
        )
        return {"response": final_response}

    except HTTPException:
        # Re-raise HTTP exceptions directly
        raise

    except Exception as e:
        logger.error(f"Unexpected error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


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
# - POST http://localhost:8000/query (with JSON body: {"agent_type": "example", "query": "your question"})
