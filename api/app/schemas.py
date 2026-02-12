import { useEffect, useState } from "react";
import { api, setToken } from "./lib/api";

type Letter = {
  id: string;
  subject: string;
  body: string;
  sendAtUtc: string;   // 后端是 datetime，前端收到是 ISO string
  status: string;
  createdAt: string;
};

export default function App() {
  // auth
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [meText, setMeText] = useState("");
  const [err, setErr] = useState("");

  // letters
  const [letters, setLetters] = useState<Letter[]>([]);
  const [loadingLetters, setLoadingLetters] = useState(false);

  // create form (matches CreateLetterReq)
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [minDays, setMinDays] = useState(180);
  const [maxDays, setMaxDays] = useState(365);
  const [creating, setCreating] = useState(false);

  async function login() {
    setErr("");
    setMeText("Logging in...");
    try {
      const data = await api<any>("/auth/login", "POST", { email, password }, false);
      const token = data.access_token ?? data.token;
      setToken(token);
      setMeText("✅ Login success, token saved");

      // 顺手拉一下 /me 和 /letters
      await fetchMe();
      await fetchLetters();
    } catch (e: any) {
      setMeText("");
      setErr(e.message ?? String(e));
    }
  }

  async function fetchMe() {
    setErr("");
    setMeText("Fetching /me ...");
    try {
      const me = await api<any>("/me", "GET");
      setMeText("✅ /me:\n" + JSON.stringify(me, null, 2));
    } catch (e: any) {
      setMeText("");
      setErr(e.message ?? String(e));
    }
  }

  async function fetchLetters() {
    setErr("");
    setLoadingLetters(true);
    try {
      const list = await api<Letter[]>("/letters", "GET");
      // 默认按 createdAt 倒序
      list.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      setLetters(list);
    } catch (e: any) {
      setErr(e.message ?? String(e));
    } finally {
      setLoadingLetters(false);
    }
  }

  async function createLetter() {
    setErr("");

    // 新手防呆：minDays <= maxDays
    if (minDays > maxDays) {
      setErr("minDays 不能大于 maxDays");
      return;
    }

    setCreating(true);
    try {
      await api<Letter>("/letters", "POST", {
        subject,
        body,
        minDays,
        maxDays,
      });

      // 清空表单
      setSubject("");
      setBody("");

      // 刷新列表
      await fetchLetters();
    } catch (e: any) {
      setErr(e.message ?? String(e));
    } finally {
      setCreating(false);
    }
  }

  async function debugSendInMinutes(letterId: string, minutes: number) {
    setErr("");
    try {
      await api(`/debug/letters/${letterId}/send_in_minutes?minutes=${minutes}`, "POST");
      await fetchLetters();
    } catch (e: any) {
      setErr(e.message ?? String(e));
    }
  }

  // 可选：页面首次打开时，尝试自动拉 /me（如果 localStorage 已经有 token）
  useEffect(() => {
    fetchMe().catch(() => {});
    fetchLetters().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1>TimeCapsule Web (MVP)</h1>

      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        {/* 左：Auth */}
        <div style={{ width: 360 }}>
          <h2 style={{ marginTop: 0 }}>Auth</h2>

          <input
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ display: "block", marginBottom: 8, padding: 8, width: "100%" }}
          />

          <input
            placeholder="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ display: "block", marginBottom: 12, padding: 8, width: "100%" }}
          />

          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <button onClick={login} style={{ padding: "8px 12px" }}>
              Login
            </button>
            <button onClick={fetchMe} style={{ padding: "8px 12px" }}>
              Fetch /me
            </button>
          </div>

          <pre style={{ whiteSpace: "pre-wrap", background: "#f6f6f6", padding: 12 }}>
            {meText}
          </pre>

          {err && (
            <div style={{ marginTop: 12, color: "crimson", whiteSpace: "pre-wrap" }}>
              ❌ {err}
            </div>
          )}
        </div>

        {/* 中：Create */}
        <div style={{ width: 420 }}>
          <h2 style={{ marginTop: 0 }}>Create Letter</h2>

          <div style={{ display: "grid", gap: 8 }}>
            <input
              placeholder="subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              style={{ padding: 8 }}
            />
            <textarea
              placeholder="body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              style={{ padding: 8, minHeight: 140 }}
            />

            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, opacity: 0.7 }}>minDays</div>
                <input
                  type="number"
                  value={minDays}
                  onChange={(e) => setMinDays(Number(e.target.value))}
                  style={{ padding: 8, width: "100%" }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, opacity: 0.7 }}>maxDays</div>
                <input
                  type="number"
                  value={maxDays}
                  onChange={(e) => setMaxDays(Number(e.target.value))}
                  style={{ padding: 8, width: "100%" }}
                />
              </div>
            </div>

            <button
              onClick={createLetter}
              disabled={!subject || !body || creating}
              style={{ padding: "10px 12px", cursor: "pointer" }}
            >
              {creating ? "Creating..." : "Create (random time in range)"}
            </button>

            <div style={{ fontSize: 12, opacity: 0.7 }}>
              说明：后端会在 minDays ~ maxDays 范围内随机生成 sendAtUtc（UTC）。
            </div>
          </div>
        </div>

        {/* 右：List */}
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Letters</h2>
            <button onClick={fetchLetters} style={{ padding: "6px 10px" }}>
              {loadingLetters ? "Loading..." : "Refresh"}
            </button>
          </div>

          <div style={{ marginTop: 12, display: "grid", gap: 12 }}>
            {letters.map((x) => (
              <div key={x.id} style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
                <div style={{ fontWeight: 600 }}>{x.subject}</div>

                <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                  status: {x.status} · sendAtUtc: {x.sendAtUtc}
                </div>

                <div style={{ fontSize: 12, opacity: 0.7 }}>
                  createdAt: {x.createdAt}
                </div>

                <div style={{ fontSize: 12, opacity: 0.7 }}>
                  id: {x.id}
                </div>

                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <button
                    onClick={() => debugSendInMinutes(x.id, 1)}
                    style={{ padding: "6px 10px" }}
                  >
                    debug: send in 1m
                  </button>
                </div>
              </div>
            ))}

            {letters.length === 0 && (
              <div style={{ opacity: 0.7, marginTop: 8 }}>
                （还没有 letters，或尚未加载）
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
