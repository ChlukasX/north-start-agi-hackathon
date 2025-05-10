import { useState, useEffect, useCallback } from "react";

const API_BASE_URL = "http://localhost:8000"; // Adjust if your backend runs elsewhere

// --- Type Definitions ---

export interface ConnectResponse {
  status: string;
  message: string;
}

export type TablesResponse = string[];

export type ColumnsResponse = string[];

export interface ApiError {
  detail: string; // Matches FastAPI's HTTPException detail
}

// New types for the /query endpoint
export interface QueryPayload {
  agent_type: string;
  query: string;
}

// Assuming the success response for /query might be more complex,
// but based on the error, the error structure is ApiError.
// If there's a specific success response structure, define it here.
// For now, we'll assume it might return a generic object or the same ApiError structure on success too.
export interface QueryResponse {
  // Example: Define what a successful response would look like
  // result?: string;
  // data?: any;
  // Or if the response structure is variable or unknown for success:
  [key: string]: any; // Allows any properties
  detail?: string; // To accommodate responses like the error example
}

// --- API Service Functions ---

/**
 * Tells the backend to connect to the database.
 */
export const connectToDb = async (): Promise<ConnectResponse> => {
  const response = await fetch(`${API_BASE_URL}/connect`, {
    method: "POST",
    // No 'Content-Type' or body is needed for this specific endpoint as defined in main.py
  });

  if (!response.ok) {
    // Attempt to parse error response from FastAPI
    const errorData: ApiError = await response
      .json()
      .catch(() => ({ detail: "Unknown error occurred" }));
    throw errorData;
  }
  return response.json();
};

/**
 * Fetches all table names from the backend.
 */
export const getAllTables = async (): Promise<TablesResponse> => {
  const response = await fetch(`${API_BASE_URL}/tables`);
  if (!response.ok) {
    const errorData: ApiError = await response
      .json()
      .catch(() => ({ detail: "Unknown error occurred" }));
    throw errorData;
  }
  return response.json();
};

/**
 * Fetches all column names for a given table from the backend.
 * @param tableName - The name of the table.
 */
export const getColumnsForTable = async (
  tableName: string,
): Promise<ColumnsResponse> => {
  if (!tableName || tableName.trim() === "") {
    // Consistent with backend, though client-side check is good too
    return Promise.reject({
      detail: "Table name cannot be empty.",
    } as ApiError);
  }

  const response = await fetch(
    `${API_BASE_URL}/tables/${encodeURIComponent(tableName)}/columns`,
  );

  if (!response.ok) {
    const errorData: ApiError = await response
      .json()
      .catch(() => ({ detail: "Unknown error occurred" }));
    throw errorData;
  }
  return response.json();
};

/**
 * Posts a query to the backend.
 * @param userQuery - The query message from the user.
 */
export const postUserQuery = async (
  userQuery: string,
): Promise<QueryResponse> => {
  if (!userQuery || userQuery.trim() === "") {
    return Promise.reject({
      detail: "Query message cannot be empty.",
    } as ApiError);
  }

  const payload: QueryPayload = {
    agent_type: "data access", // As per your curl command
    query: userQuery,
  };

  const response = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  // The response might be an error (like the API key issue) or a success.
  // FastAPI often returns JSON for both, and HTTP status codes differentiate.
  const responseData = await response.json().catch(() => {
    // If JSON parsing fails for a non-OK response, create a generic error
    if (!response.ok) {
      return { detail: `Request failed with status ${response.status}` };
    }
    // If JSON parsing fails for an OK response, it's unexpected
    return { detail: "Failed to parse response JSON." };
  });

  if (!response.ok) {
    // Ensure the errorData conforms to ApiError or QueryResponse (which includes detail)
    throw responseData as ApiError;
  }

  return responseData as QueryResponse;
};

// --- React Hooks ---

/**
 * Hook to manage connecting to the database.
 * Provides a `connect` function and states for loading, error, and data.
 */
export const useConnectToDb = () => {
  const [data, setData] = useState<ConnectResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  const connect = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await connectToDb();
      setData(result);
      setIsLoading(false);
      return result;
    } catch (err) {
      setError(err as ApiError);
      setIsLoading(false);
      throw err; // Re-throw for component-level handling if needed
    }
  }, []);

  return { connect, data, isLoading, error };
};

/**
 * Hook to manage fetching all table names.
 * Provides a `WorkspaceTables` function and states for loading, error, and data.
 */
export const useGetAllTables = () => {
  const [data, setData] = useState<TablesResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  const fetchTables = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getAllTables();
      setData(result);
      setIsLoading(false);
      return result;
    } catch (err) {
      setError(err as ApiError);
      setIsLoading(false);
      throw err;
    }
  }, []);

  return { fetchTables, data, isLoading, error };
};

/**
 * Hook to manage fetching columns for a specific table.
 * @param initialTableName - Optional. If provided, columns for this table will be fetched on mount.
 * Provides a `WorkspaceColumns` function and states for loading, error, and data.
 * Also returns `WorkspaceedForTable` to indicate which table the current data belongs to.
 */
export const useGetColumnsForTable = (initialTableName?: string | null) => {
  const [data, setData] = useState<ColumnsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [fetchedForTable, setFetchedForTable] = useState<string | null>(null);

  const fetchColumns = useCallback(async (tableName: string) => {
    if (!tableName || tableName.trim() === "") {
      setData(null);
      setFetchedForTable(null);
      setError({ detail: "Table name is required to fetch columns." }); // Set an error state
      return; // Don't attempt to fetch
    }

    setIsLoading(true);
    setError(null);
    try {
      const result = await getColumnsForTable(tableName);
      setData(result);
      setFetchedForTable(tableName);
      setIsLoading(false);
      return result;
    } catch (err) {
      setError(err as ApiError);
      setData(null); // Clear data on error
      setFetchedForTable(null); // Clear associated table name on error
      setIsLoading(false);
      throw err;
    }
  }, []); // getColumnsForTable is stable (module scope)

  useEffect(() => {
    if (initialTableName && initialTableName.trim() !== "") {
      fetchColumns(initialTableName);
    } else {
      // If initialTableName is null, empty, or whitespace, ensure no data is shown.
      setData(null);
      setFetchedForTable(null);
      // Optionally clear error or set a specific state if needed
      // setError(null);
    }
  }, [initialTableName, fetchColumns]); // Re-run if initialTableName or fetchColumns changes

  return { fetchColumns, data, isLoading, error, fetchedForTable };
};

/**
 * Hook to manage posting a user query.
 * Provides a `submitQuery` function and states for loading, error, and data.
 */
export const useSubmitQuery = () => {
  const [data, setData] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  const submitQuery = useCallback(async (userQuery: string) => {
    if (!userQuery || userQuery.trim() === "") {
      setError({ detail: "Query message cannot be empty." });
      setData(null);
      return; // Don't attempt to submit
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await postUserQuery(userQuery);
      setData(result);
      setIsLoading(false);
      // If the result itself contains a 'detail' field and implies an error
      // (e.g. the Google API key error, which might come with a 200 OK or a specific error code)
      // you might want to move it to the error state.
      // However, the current postUserQuery throws an error for non-ok responses.
      // If 'detail' can appear in successful (2xx) responses as an error message:
      if (result.detail && responseIndicatesError(result)) {
        // You'd need a helper responseIndicatesError
        setError({ detail: result.detail });
        setData(null); // Clear data if it's considered an error
      }
      return result;
    } catch (err) {
      setError(err as ApiError);
      setData(null);
      setIsLoading(false);
      throw err; // Re-throw for component-level handling if needed
    }
  }, []);

  // Helper function to determine if a response, even if 2xx, indicates an error
  // This is an example, you might need to adjust its logic based on your API behavior
  const responseIndicatesError = (response: QueryResponse): boolean => {
    // Example: if the response has a 'detail' field and no other 'success' field
    return typeof response.detail === "string" && !response.successProperty; // Adjust 'successProperty'
  };

  return { submitQuery, data, isLoading, error };
};
