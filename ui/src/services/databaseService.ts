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

// Updated types for the /chat endpoint
export interface QueryPayload {
  session_id: string; // Changed from agent_type
  message: string; // Changed from query
}

export interface QueryResponse {
  // To ensure compatibility with chat.tsx, we expect a 'response' field for the AI message.
  response?: string; // For the AI's textual reply e.g. {"response": "Hello there!"}
  [key: string]: any; // Allows other properties that might come with the response
  detail?: string; // To accommodate responses like FastAPI error details
}

// --- API Service Functions ---

/**
 * Tells the backend to connect to the database.
 */
export const connectToDb = async (): Promise<ConnectResponse> => {
  const response = await fetch(`${API_BASE_URL}/connect`, {
    method: "POST",
  });

  if (!response.ok) {
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
 * Posts a chat message to the backend.
 * @param userMessageContent - The message content from the user.
 */
export const postUserQuery = async (
  // Renaming userQuery to userMessageContent for clarity internally
  userMessageContent: string,
): Promise<QueryResponse> => {
  if (!userMessageContent || userMessageContent.trim() === "") {
    return Promise.reject({
      detail: "Message content cannot be empty.", // Updated error message
    } as ApiError);
  }

  // Updated payload structure
  const payload: QueryPayload = {
    session_id: "u123", // As per your curl command example
    message: userMessageContent,
  };

  // Updated endpoint to /chat
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const responseData = await response.json().catch(() => {
    if (!response.ok) {
      return { detail: `Request failed with status ${response.status}` };
    }
    return { detail: "Failed to parse response JSON." };
  });

  if (!response.ok) {
    throw responseData as ApiError;
  }

  return responseData as QueryResponse;
};

// --- React Hooks ---

/**
 * Hook to manage connecting to the database.
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
      throw err;
    }
  }, []);

  return { connect, data, isLoading, error };
};

/**
 * Hook to manage fetching all table names.
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
      setError({ detail: "Table name is required to fetch columns." });
      return;
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
      setData(null);
      setFetchedForTable(null);
      setIsLoading(false);
      throw err;
    }
  }, []);

  useEffect(() => {
    if (initialTableName && initialTableName.trim() !== "") {
      fetchColumns(initialTableName);
    } else {
      setData(null);
      setFetchedForTable(null);
    }
  }, [initialTableName, fetchColumns]);

  return { fetchColumns, data, isLoading, error, fetchedForTable };
};

/**
 * Hook to manage posting a user message and getting a chat response.
 */
export const useSubmitQuery = () => {
  // Hook name remains the same for minimal changes in chat.tsx
  const [data, setData] = useState<QueryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<ApiError | null>(null);

  // The parameter 'userQuery' from chat.tsx will become the 'message' in the payload.
  const submitQuery = useCallback(async (userMessageContent: string) => {
    if (!userMessageContent || userMessageContent.trim() === "") {
      setError({ detail: "Message content cannot be empty." }); // Updated error message
      setData(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    setData(null); // Clear previous data
    try {
      const result = await postUserQuery(userMessageContent); // postUserQuery now uses /chat
      setData(result);
      setIsLoading(false);

      // The responseIndicatesError logic might need adjustment if the /chat
      // endpoint has a different way of signaling errors in a 2xx response.
      // For now, assuming 'detail' in a 2xx response is still an error indicator.
      if (result.detail && responseIndicatesError(result)) {
        setError({ detail: result.detail });
        setData(null);
      }
      return result;
    } catch (err) {
      setError(err as ApiError);
      setData(null);
      setIsLoading(false);
      throw err;
    }
  }, []);

  // This helper might need adjustment based on how your /chat endpoint signals
  // application-level errors within a successful HTTP response.
  const responseIndicatesError = (response: QueryResponse): boolean => {
    // Example: if the response has a 'detail' field and no 'response' field (actual chat reply)
    return (
      typeof response.detail === "string" &&
      typeof response.response === "undefined"
    );
  };

  return { submitQuery, data, isLoading, error };
};
