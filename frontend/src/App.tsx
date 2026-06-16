import { useState } from "react";
import EngagementPage from "./pages/EngagementPage";
import MissilePage from "./pages/MissilePage";
import MotorPage from "./pages/MotorPage";
import ItemsPage from "./pages/ItemsPage";
import "./App.css";

type Tab = "engagement" | "motor" | "missile" | "items";

const TABS: { id: Tab; label: string }[] = [
  { id: "engagement", label: "Interception" },
  { id: "motor", label: "Motor" },
  { id: "missile", label: "Trajectory" },
  { id: "items", label: "Items" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("engagement");

  return (
    <main>
      <header className="app-header">
        <h1>Interceptor &amp; Solid-Motor Simulator</h1>
        <p className="subtitle">
          Parametric internal ballistics, flight dynamics and PN interception —
          with CAD and Simulink export.
        </p>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? "tab active" : "tab"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {tab === "engagement" && <EngagementPage />}
      {tab === "motor" && <MotorPage />}
      {tab === "missile" && <MissilePage />}
      {tab === "items" && <ItemsPage />}
    </main>
  );
}
