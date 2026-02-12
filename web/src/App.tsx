import { useState } from "react";
import { api, setToken } from "./lib/api";

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [text, setText] = useState("");

  async function login() {
    setText("Logging in...");
    try {
      const data = await api<any>(
        "/auth/login",
        "POST",
        { email, password },
        false
      );

      const token = data.access_token ?? data.token;
      setToken(token);

      setText("✅ Login success, token saved");
    } catch (e: any) {
      setText("❌ " + (e.message ?? e));
    }
  }

  async function fetchMe() {
    setText("Fetching /me ...");
    try {
      const me = await api<any>("/me", "GET");
      setText("✅ /me:\n" + JSON.stringify(me, null, 2));
    } catch (e: any) {
      setText("❌ " + (e.message ?? e));
    }
  }

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1>TimeCapsule Login Test</h1>

      <input
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{ display: "block", marginBottom: 8, padding: 8, width: 320 }}
      />

      <input
        placeholder="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ display: "block", marginBottom: 12, padding: 8, width: 320 }}
      />

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={login} style={{ padding: "8px 12px" }}>
          Login
        </button>

        <button onClick={fetchMe} style={{ padding: "8px 12px" }}>
          Fetch /me
        </button>
      </div>

      <pre style={{ marginTop: 16, whiteSpace: "pre-wrap" }}>{text}</pre>
    </div>
  );
}
