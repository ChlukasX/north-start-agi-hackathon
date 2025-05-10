import psycopg2

class PostgresDB:
    """
    A class to interact with a PostgreSQL database using psycopg2.
    It provides functionalities to connect, disconnect, list all tables,
    and list columns of a specific table.
    """
    def __init__(self, dbname="devdb", user="devuser", password="devpassword", host="localhost", port="5433"):
        """
        Initializes the PostgresDB object with database connection parameters.

        Args:
            dbname (str): The name of the database.
            user (str): The username for database authentication.
            password (str): The password for database authentication.
            host (str): The host address of the database server.
            port (str): The port number for the database server.
        """
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.connection = None
        self.cursor = None
        # For FastAPI to easily check status if needed, without exposing psycopg2 objects directly
        self._is_connected = False

    def connect(self):
        """
        Establishes a connection to the PostgreSQL database.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
        if self.connection:
            print("Already connected to the database.")
            self._is_connected = True
            return True
        try:
            print(f"Attempting to connect to database: {self.dbname}@{self.host}:{self.port} with user {self.user}")
            self.connection = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            self.cursor = self.connection.cursor()
            self._is_connected = True
            print("Successfully connected to the database.")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to the database: {e}")
            self.connection = None
            self.cursor = None
            self._is_connected = False
            return False
        except Exception as e:
            print(f"An unexpected error occurred during connection: {e}")
            self.connection = None
            self.cursor = None
            self._is_connected = False
            return False

    def disconnect(self):
        """
        Closes the database connection and cursor.

        Returns:
            bool: True if disconnection is successful or if not connected, False otherwise.
        """
        closed_something = False
        if self.cursor:
            try:
                self.cursor.close()
                self.cursor = None
                print("Cursor closed.")
                closed_something = True
            except Exception as e:
                print(f"Error closing cursor: {e}")
                # Continue to attempt closing connection
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                print("Database connection closed.")
                closed_something = True
            except Exception as e:
                print(f"Error closing connection: {e}")

        self._is_connected = False
        if not closed_something and not self.connection and not self.cursor:
            print("No active connection or cursor to disconnect.")
            return True # Considered successful if already disconnected
        return True # Assuming success if attempts were made, errors printed

    def get_all_tables(self):
        """
        Retrieves a list of all user-defined tables in the connected database.

        Returns:
            list: A list of table names. Returns an empty list if no tables
                  are found or if an error occurs or not connected.
        """
        if not self._is_connected or not self.cursor:
            print("Not connected to the database. Please connect first.")
            return []
        try:
            self.cursor.execute("""
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';
            """)
            tables = [table[0] for table in self.cursor.fetchall()]
            return tables
        except psycopg2.Error as e:
            print(f"Error fetching tables: {e}")
            # If a query fails, the connection might be in an unusable state.
            # Depending on the error, a reconnect might be needed.
            # For simplicity here, we just return empty.
            return []
        except Exception as e:
            print(f"An unexpected error occurred while fetching tables: {e}")
            return []

    def get_table_columns(self, table_name):
            """
            Retrieves a list of all column names for a specified table.

            Args:
                table_name (str): The name of the table.

            Returns:
                list: A list of column names. Returns an empty list if the table
                      does not exist, has no columns, or if an error occurs or not connected.
            """
            if not self._is_connected or not self.cursor:
                print("Not connected to the database. Please connect first.")
                return []
            if not table_name or not isinstance(table_name, str):
                print("Invalid table name provided.")
                return []
            try:
                # Check if table exists
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_name = %s AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    );
                """, (table_name,))
                # Fetch the result and check if it's None before accessing index [0]
                table_exists_result = self.cursor.fetchone()
                if table_exists_result is None or not table_exists_result[0]:
                    print(f"Table '{table_name}' does not exist in user schemas or query failed.")
                    return []

                query = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """
                self.cursor.execute(query, (table_name,))
                columns = [column[0] for column in self.cursor.fetchall()]
                return columns
            except psycopg2.Error as e:
                print(f"Error fetching columns for table '{table_name}': {e}")
                return []
            except Exception as e:
                print(f"An unexpected error occurred while fetching columns for table '{table_name}': {e}")
                return []

    @property
    def is_connected(self):
        """Simple property to check connection status."""
        return self._is_connected
