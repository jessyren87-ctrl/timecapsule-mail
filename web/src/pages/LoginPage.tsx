import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../lib/api";

export default function LoginPage() {
  const nav = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  async function login() {
    setErr("");
    try {
      const data = await api<any>("/auth/login", "POST", { email, password }, false);
      const token = data.access_token ?? data.token;
      setToken(token);

      nav("/app"); // 登录成功跳转
    } catch (e: any) {
      setErr(e.message ?? String(e));
    }
  }

  return (
    <div style={{ padding: 40 }}>
      <h1>Login</h1>

      <input
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{ display: "block", marginBottom: 8, padding: 8, width: 260 }}
      />

      <input
        placeholder="password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        style={{ display: "block", marginBottom: 12, padding: 8, width: 260 }}
      />

      <button onClick={login} style={{ padding: "8px 12px" }}>
        Login
      </button>

      {err && <div style={{ color: "crimson", marginTop: 12 }}>{err}</div>}
    </div>
  );
}
