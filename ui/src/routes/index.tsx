import { createFileRoute, useNavigate } from "@tanstack/react-router";
import databaseIcon from "../assets/database.svg";
import dataTableIcon from "../assets/data-table.svg";
import "../App.css";

export const Route = createFileRoute("/")({
  component: App,
});

function App() {
  const navigation = useNavigate();
  const handleStart = () => {
    navigation({ to: "/chat" });
  };

  return (
    <div className="hero min-h-screen">
      <div className="hero-overlay "></div>
      <div className="hero-content text-center text-neutral-content ">
        <div className="max-w-md">
          <div className="flex justify-center mb-5">
            <img
              src={databaseIcon}
              className="App-logo h-24 w-24 mx-5 invert"
              alt="database icon"
            />
            <img
              src={dataTableIcon}
              className="App-logo h-24 w-24 mx-5 invert"
              alt="data table icon"
            />
          </div>
          <h1 className="mb-5 text-5xl font-bold">DataCrawler</h1>
          <p className="mb-5">Make sense of your data with the power of AI.</p>
          <button
            onClick={handleStart}
            className="btn btn-primary btn-xs sm:btn-sm md:btn-md lg:btn-lg xl:btn-xl"
          >
            Start
          </button>
        </div>
      </div>
    </div>
  );
}
