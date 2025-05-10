import { createFileRoute } from "@tanstack/react-router";
import aiIcon from "../assets/robot-icon.svg";
import userIcon from "../assets/user.svg";
import databaseIcon from "../assets/database.svg";
import { useEffect, useState, useRef } from "react"; // Added useRef
import {
  useConnectToDb,
  useGetAllTables,
  useGetColumnsForTable,
  useSubmitQuery, // Import the new hook
} from "../services/databaseService"; // Assuming databaseService.ts is in ../services/

export const Route = createFileRoute("/chat")({
  component: ChatComponent,
});

const SendIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className="w-6 h-6"
  >
    <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
  </svg>
);

// Define a type for your message objects
interface Message {
  id: number;
  text: string;
  sender: "ai" | "user" | "system"; // Added "system" for error messages
  detail?: string; // For displaying API error details
}

function ChatComponent() {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: "Hello! How can I help you today?", sender: "ai" },
    // Example initial messages removed for brevity, can be added back if needed
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isConnectedToDb, setIsConnectedToDb] = useState(false);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null); // For scrolling to the bottom

  // --- Hooks from databaseService ---
  const {
    connect: connectToDbService,
    data: connectData, // Keep if used, otherwise can be removed if only status matters
    isLoading: isConnectingDb,
    error: connectDbError,
  } = useConnectToDb();

  const {
    fetchTables,
    data: allTablesData, // Keep if used directly
    isLoading: isLoadingTables,
    error: tablesError,
  } = useGetAllTables();

  const {
    fetchColumns,
    data: tableColumnsData, // Keep if used directly
    isLoading: isLoadingColumns,
    error: columnsError,
    // fetchedForTable,
  } = useGetColumnsForTable();

  // --- Hook for submitting queries ---
  const {
    submitQuery,
    data: queryData,
    isLoading: isQueryLoading,
    error: queryError,
  } = useSubmitQuery();

  const [availableTables, setAvailableTables] = useState<string[] | null>(null);
  const [availableColumns, setAvailableColumns] = useState<string[] | null>(
    null,
  );

  // Scroll to bottom of messages when messages change
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async () => {
    if (inputValue.trim() === "") return;

    const userMessage: Message = {
      id: Date.now(),
      text: inputValue,
      sender: "user",
    };
    setMessages((prevMessages) => [...prevMessages, userMessage]);

    try {
      // Call the submitQuery function from the hook
      await submitQuery(inputValue);
      // The AI response will be handled by the useEffect watching queryData
    } catch (err) {
      // Error is already handled by the queryError state and useEffect below
      // You could add a specific user-facing message here if the hook's error isn't immediate
      console.error("Error sending message:", err);
    }

    setInputValue("");
  };

  // Effect to handle successful AI responses
  useEffect(() => {
    if (queryData) {
      let aiText = "Sorry, I couldn't understand the response."; // Default message if parsing fails

      // ** NEW: Check for the "response" field first **
      if (queryData && typeof queryData.response === "string") {
        aiText = queryData.response;
      } else if (typeof queryData.detail === "string") {
        // For error messages like API key issues
        aiText = queryData.detail;
      } else if (typeof queryData.message === "string") {
        // Another common field for messages
        aiText = queryData.message;
      } else if (queryData.result && typeof queryData.result === "string") {
        // If response is in a 'result' field
        aiText = queryData.result;
      } else if (typeof queryData === "string") {
        // If the entire queryData is just a string
        aiText = queryData;
      }
      // Optionally, keep a JSON stringify for debugging if none of the above match and it's an object
      // else if (typeof queryData === 'object' && queryData !== null) {
      //   aiText = JSON.stringify(queryData);
      // }

      setMessages((prevMessages) => [
        ...prevMessages,
        { id: Date.now() + 1, text: aiText, sender: "ai" },
      ]);
    }
  }, [queryData]);

  // Effect to handle errors from submitting queries
  useEffect(() => {
    if (queryError) {
      setMessages((prevMessages) => [
        ...prevMessages,
        {
          id: Date.now(),
          text:
            "Error from AI: " +
            (queryError.detail || "An unknown error occurred."),
          sender: "system", // Use 'system' or 'ai' with an error style
          detail: queryError.detail,
        },
      ]);
    }
  }, [queryError]);

  const handleConnectToDb = async () => {
    try {
      const result = await connectToDbService();
      if (result && result.status === "success") {
        // Check specific success status if available
        setIsConnectedToDb(true);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            text: result.message || "Successfully connected to database.",
            sender: "system",
          },
        ]);
        setSelectedTable(null);
        setSelectedColumn(null);
        setAvailableTables(null);
        setAvailableColumns(null);
      } else if (result) {
        // Handle cases where result exists but isn't a clear success
        setIsConnectedToDb(false);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            text:
              result.message ||
              "Connection attempt returned a response, but status is unclear.",
            sender: "system",
          },
        ]);
      }
    } catch (err: any) {
      setIsConnectedToDb(false);
      const errorMessage =
        err?.detail || "Failed to connect to the database. Unknown error.";
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: `DB Connection Error: ${errorMessage}`,
          sender: "system",
        },
      ]);
      console.error("Connection error:", err);
    }
  };

  const handleChooseTable = async () => {
    if (!isConnectedToDb) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: "Please connect to the database first.",
          sender: "system",
        },
      ]);
      return;
    }
    try {
      const tables = await fetchTables();
      if (tables && tables.length > 0) {
        setAvailableTables(tables);
        setSelectedTable(tables[0]); // Auto-select first table for demo
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            text: `Available tables loaded. Selected: ${tables[0]}`,
            sender: "system",
          },
        ]);
        setSelectedColumn(null);
        setAvailableColumns(null);
        // Automatically try to fetch columns for the auto-selected table
        await handleChooseColumn(tables[0]);
      } else if (tables) {
        setAvailableTables([]);
        setSelectedTable(null);
        setSelectedColumn(null);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            text: "No tables found in the database.",
            sender: "system",
          },
        ]);
      }
    } catch (err: any) {
      const errorMessage =
        err?.detail || "Failed to fetch tables. Unknown error.";
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: `Error fetching tables: ${errorMessage}`,
          sender: "system",
        },
      ]);
      setAvailableTables(null);
      setSelectedTable(null);
      setSelectedColumn(null);
      console.error("Fetch tables error:", err);
    }
  };

  // Modified to accept tableName to be called directly
  const handleChooseColumn = async (tableName?: string) => {
    const tableToFetch = tableName || selectedTable;
    if (!tableToFetch) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: "No table selected to fetch columns for.",
          sender: "system",
        },
      ]);
      return;
    }
    try {
      const columns = await fetchColumns(tableToFetch);
      if (columns && columns.length > 0) {
        setAvailableColumns(columns);
        setSelectedColumn(columns[0]); // Auto-select first for demo
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            text: `Columns for ${tableToFetch} loaded. Selected: ${columns[0]}`,
            sender: "system",
          },
        ]);
      } else if (columns) {
        setAvailableColumns([]);
        setSelectedColumn(null);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now(),
            text: `No columns found for table ${tableToFetch}.`,
            sender: "system",
          },
        ]);
      }
    } catch (err: any) {
      const errorMessage =
        err?.detail ||
        `Failed to fetch columns for table "${tableToFetch}". Unknown error.`;
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: `Error fetching columns: ${errorMessage}`,
          sender: "system",
        },
      ]);
      setAvailableColumns(null);
      setSelectedColumn(null);
      console.error("Fetch columns error:", err);
    }
  };

  // Effects for DB operation errors
  useEffect(() => {
    if (connectDbError) {
      setIsConnectedToDb(false);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: `DB Connection Error: ${connectDbError.detail || "Unknown error."}`,
          sender: "system",
        },
      ]);
    }
  }, [connectDbError]);

  useEffect(() => {
    if (tablesError) {
      setAvailableTables(null);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: `Error fetching tables: ${tablesError.detail || "Unknown error."}`,
          sender: "system",
        },
      ]);
    }
  }, [tablesError]);

  useEffect(() => {
    if (columnsError) {
      setAvailableColumns(null);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          text: `Error fetching columns: ${columnsError.detail || "Unknown error."}`,
          sender: "system",
        },
      ]);
    }
  }, [columnsError]);

  return (
    <div className="flex flex-col h-screen bg-base-200">
      {/* Header */}
      <header className="navbar bg-base-100 shadow">
        <div className="flex-1">
          <a className="btn btn-ghost normal-case text-xl">DataCrawler</a>
        </div>
      </header>

      {/* Chat Messages Area */}
      <div className="flex-grow p-6 overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat ${
              msg.sender === "user"
                ? "chat-end"
                : msg.sender === "ai"
                  ? "chat-start"
                  : "chat-start" // System messages also start
            }`}
          >
            <div className="chat-image avatar">
              <div className="w-10 rounded-full">
                <img
                  className={
                    msg.sender === "ai" || msg.sender === "system"
                      ? "invert"
                      : ""
                  } // Invert AI and System icons
                  alt={
                    msg.sender === "user"
                      ? "User Avatar"
                      : msg.sender === "ai"
                        ? "AI Avatar"
                        : "System Icon"
                  }
                  src={
                    msg.sender === "user"
                      ? userIcon
                      : msg.sender === "ai"
                        ? aiIcon
                        : databaseIcon // System messages use database icon or other
                  }
                />
              </div>
            </div>
            <div
              className={`chat-bubble ${
                msg.sender === "user"
                  ? "chat-bubble-primary"
                  : msg.sender === "ai"
                    ? "chat-bubble-neutral"
                    : "chat-bubble-accent" // System messages style
              }`}
            >
              {msg.text}
              {msg.sender === "system" && msg.detail && (
                <p className="text-xs opacity-70 mt-1">{msg.detail}</p>
              )}
            </div>
            <div className="chat-footer opacity-50">
              <time className="text-xs">
                {new Date(msg.id).toLocaleTimeString([], {
                  // Use message ID for time if it's a timestamp
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </time>
            </div>
          </div>
        ))}
        {isQueryLoading && (
          <div className="chat chat-start">
            <div className="chat-image avatar">
              <div className="w-10 rounded-full">
                <img className="invert" alt="AI Avatar" src={aiIcon} />
              </div>
            </div>
            <div className="chat-bubble chat-bubble-neutral">
              <span className="loading loading-dots loading-md"></span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} /> {/* Element to scroll to */}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-base-100 border-t border-base-300">
        <div className="join w-full">
          <input
            type="text"
            placeholder="Type your message here..."
            className="input input-bordered join-item flex-grow"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !isQueryLoading) {
                // Prevent send while loading
                handleSendMessage();
              }
            }}
            disabled={
              isQueryLoading ||
              isConnectingDb ||
              isLoadingTables ||
              isLoadingColumns
            }
          />
          <div className="dropdown dropdown-top dropdown-end join-item">
            {" "}
            {/* join-item instead of join-vertical */}
            <button
              tabIndex={0}
              role="button"
              className="btn btn-info h-full"
              disabled={isQueryLoading}
            >
              {" "}
              {/* h-full to match input height */}
              <img
                src={databaseIcon}
                alt="Database Options"
                className="h-6 w-6 invert"
              />
            </button>
            ,
            <ul
              tabIndex={0}
              className="dropdown-content z-[1] menu p-2 shadow bg-base-300 rounded-box w-64" // Increased width
            >
              <li className="flex flex-col items-center">
                <button
                  onClick={handleConnectToDb}
                  className="btn btn-sm btn-ghost w-full justify-center"
                  disabled={isConnectedToDb || isConnectingDb}
                >
                  {isConnectingDb ? (
                    <span className="loading loading-spinner loading-xs"></span>
                  ) : (
                    "Connect to Database"
                  )}
                </button>
                <div
                  className={`badge ${
                    isConnectingDb
                      ? "badge-warning"
                      : isConnectedToDb
                        ? "badge-success"
                        : "badge-error"
                  } w-full pointer-events-none`}
                >
                  {isConnectingDb
                    ? "Connecting..."
                    : connectDbError
                      ? "Error"
                      : isConnectedToDb
                        ? "Connected"
                        : "Not Connected"}
                </div>
                {connectDbError && (
                  <p className="text-error text-xs px-2 w-full text-center">
                    {connectDbError.detail}
                  </p>
                )}
              </li>
              <li className="menu-title">
                <span>Database Schema</span>
              </li>
              <li>
                <button
                  onClick={() => handleChooseTable()}
                  className="btn btn-sm btn-ghost w-full justify-between" // justify-between for badge alignment
                  disabled={
                    !isConnectedToDb || isLoadingTables || isConnectingDb
                  }
                >
                  {isLoadingTables ? (
                    <span className="loading loading-spinner loading-xs"></span>
                  ) : (
                    "Tables"
                  )}
                  <span
                    className={`badge ${selectedTable ? "badge-success" : "badge-ghost"}`}
                  >
                    {selectedTable
                      ? selectedTable.substring(0, 15) +
                        (selectedTable.length > 15 ? "..." : "")
                      : "None"}
                  </span>
                </button>
                {tablesError && (
                  <p className="text-error text-xs px-2">
                    {tablesError.detail}
                  </p>
                )}
                {/* Optional: Display list of available tables if fetched */}
                {availableTables && availableTables.length > 0 && (
                  <div className="max-h-32 overflow-y-auto bg-base-200 rounded p-1 my-1">
                    {availableTables.map((table) => (
                      <button
                        key={table}
                        onClick={() => {
                          setSelectedTable(table);
                          setAvailableColumns(null);
                          setSelectedColumn(null);
                          handleChooseColumn(table);
                          (document.activeElement as HTMLElement)?.blur();
                        }}
                        className={`btn btn-xs btn-ghost w-full justify-start ${selectedTable === table ? "btn-active" : ""}`}
                      >
                        {table}
                      </button>
                    ))}
                  </div>
                )}
              </li>
              <li>
                <button
                  onClick={() => handleChooseColumn()}
                  className="btn btn-sm btn-ghost w-full justify-between"
                  disabled={
                    !selectedTable || isLoadingColumns || isConnectingDb
                  }
                >
                  {isLoadingColumns ? (
                    <span className="loading loading-spinner loading-xs"></span>
                  ) : (
                    "Columns"
                  )}
                  <span
                    className={`badge ${selectedColumn ? "badge-success" : "badge-ghost"}`}
                  >
                    {selectedColumn
                      ? selectedColumn.substring(0, 15) +
                        (selectedColumn.length > 15 ? "..." : "")
                      : "None"}
                  </span>
                </button>
                {columnsError && (
                  <p className="text-error text-xs px-2">
                    {columnsError.detail}
                  </p>
                )}
                {/* Optional: Display list of available columns if fetched */}
                {availableColumns &&
                  availableColumns.length > 0 &&
                  selectedTable && (
                    <div className="max-h-32 overflow-y-auto bg-base-200 rounded p-1 my-1">
                      {availableColumns.map((col) => (
                        <button
                          key={col}
                          onClick={() => {
                            setSelectedColumn(col);
                            (document.activeElement as HTMLElement)?.blur();
                          }}
                          className={`btn btn-xs btn-ghost w-full justify-start ${selectedColumn === col ? "btn-active" : ""}`}
                        >
                          {col}
                        </button>
                      ))}
                    </div>
                  )}
              </li>
            </ul>
          </div>
          <button
            className="btn btn-primary join-item"
            onClick={handleSendMessage}
            disabled={
              isQueryLoading ||
              inputValue.trim() === "" ||
              isConnectingDb ||
              isLoadingTables ||
              isLoadingColumns
            }
          >
            {isQueryLoading ? (
              <span className="loading loading-spinner loading-xs"></span>
            ) : (
              <SendIcon />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
