"use client";
import { useEffect, useState } from "react";
import { autoLogin, chat, apiGet, apiPost } from "@/lib/api";

type Dashboard = {
  wallet: { allocated_balance: number; currency: string; real_money_note: string };
  stop_loss: { halted: boolean; reason: string };
  total_revenue: number;
  counts: Record<string, number>;
  strategies: { name: string; enabled: boolean; risk: string }[];
  recent_executions: { strategy: string; action: string; time: string; revenue: number }[];
};

type Strategy = {
  id: number; name: string; display_name: string;
  enabled: boolean; risk_level: string;
  daily_profit_target: number; daily_loss_limit: number;
};

type LogEntry = {
  type: string;
  source: string;
  action: string;
  detail: string;
  result?: string;
  level?: string;
  revenue?: number;
  profit?: number;
  time: string;
};

export default function Home() {
  const [ready, setReady] = useState(false);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [msg, setMsg] = useState("");
  const [chatLog, setChatLog] = useState<{ role: string; text: string }[]>([]);
  const [activeTab, setActiveTab] = useState("dashboard");

  // Existing state (keep for backward compat)
  const [balance, setBalance] = useState<any>(null);
  const [ledger, setLedger] = useState<any[]>([]);
  const [notifs, setNotifs] = useState<any[]>([]);
  const [deals, setDeals] = useState<any[]>([]);
  const [depAmt, setDepAmt] = useState("100");
  const [dealCust, setDealCust] = useState("");
  const [dealTitle, setDealTitle] = useState("");
  const [dealAmt, setDealAmt] = useState("100");
  const [dealCost, setDealCost] = useState("0");

  async function refreshAll() {
    try {
      const [b, l, n, d, dash, strats, logEntries] = await Promise.all([
        apiGet("/api/balance"),
        apiGet("/api/ledger"),
        apiGet("/api/notifications"),
        apiGet("/api/deals"),
        apiGet("/api/dashboard/summary"),
        apiGet("/api/strategies"),
        apiGet("/api/agent/logs?limit=100"),
      ]);
      setBalance(b);
      setLedger(l);
      setNotifs(n);
      setDeals(d);
      setDashboard(dash);
      setStrategies(strats);
      setLogs(logEntries);
    } catch (e) {
      console.error(e);
    }
  }

  // Auto-login on mount (personal mode — no password)
  useEffect(() => {
    (async () => {
      try {
        await autoLogin();
        setReady(true);
      } catch (e) {
        console.error("Auto-login failed", e);
        setReady(true);
      }
    })();
  }, []);

  useEffect(() => {
    if (ready) refreshAll();
  }, [ready]);

  // Poll logs every 10 seconds for live updates
  useEffect(() => {
    if (!ready) return;
    const interval = setInterval(refreshAll, 10000);
    return () => clearInterval(interval);
  }, [ready]);

  async function doChat() {
    if (!msg.trim()) return;
    setChatLog((c) => [...c, { role: "user", text: msg }]);
    setMsg("");
    const reply = await chat(msg);
    setChatLog((c) => [...c, { role: "agent", text: reply }]);
    refreshAll();
  }

  async function runCycle() {
    const result = await apiPost("/api/strategies/run-cycle", {});
    await refreshAll();
    alert(JSON.stringify(result, null, 2));
  }

  async function runAll() {
    const result = await apiPost("/api/strategies/run-all", {});
    await refreshAll();
    alert(`${result.strategies_run} strategies executed`);
  }

  async function toggleStrategy(name: string, enabled: boolean) {
    await apiPost(`/api/strategies/${name}/toggle`, { enabled });
    await refreshAll();
  }

  async function doDeposit() {
    await apiPost("/api/deposit", { amount: parseFloat(depAmt) });
    await refreshAll();
  }

  async function doDeal() {
    await apiPost("/api/deals", {
      customer: dealCust, title: dealTitle,
      amount: parseFloat(dealAmt), cost: parseFloat(dealCost || "0"),
    });
    setDealCust(""); setDealTitle(""); setDealAmt("100"); setDealCost("0");
    await refreshAll();
  }

  async function confirmPayment(dealId: number) {
    await apiPost("/api/deals/confirm-payment", { deal_id: dealId });
    await refreshAll();
  }

  const riskColor = (r: string) => r === "high" ? "#f87171" : r === "medium" ? "#fbbf24" : "#4ade80";

  const logColor = (level: string) =>
    level === "danger" ? "#f87171" : level === "success" ? "#4ade80" : level === "warning" ? "#fbbf24" : "#94a3b8";

  const logIcon = (type: string) => {
    if (type === "strategy") return "⚙️";
    if (type === "notification") return "🔔";
    if (type === "chat") return "💬";
    return "🤖";
  };

  const formatTime = (t: string) => {
    const d = new Date(t);
    return d.toLocaleTimeString();
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a", color: "#e2e8f0" }}>
      {/* SIDEBAR */}
      <div style={{ width: 220, background: "#1e293b", padding: "16px 0", borderRight: "1px solid #334155" }}>
        <div style={{ padding: "0 16px 16px", borderBottom: "1px solid #334155", marginBottom: 8 }}>
          <h2 style={{ fontSize: 18, margin: 0 }}>🤖 Agent Experts</h2>
          <span style={{ fontSize: 11, color: "#4ade80" }}>AI Earning Machine</span>
        </div>
        {[
          ["dashboard", "📊 Dashboard"],
          ["logs", "📜 Agent Logs"],
          ["products", "🎁 Products"],
          ["coding", "💻 Coding"],
          ["content", "📝 Content"],
          ["trading", "📈 Trading"],
          ["freelance", "🔍 Freelance"],
          ["business", "🏢 Business"],
          ["finances", "💰 Finances"],
        ].map(([key, label]) => (
          <div key={key} onClick={() => setActiveTab(key)}
            style={{
              padding: "10px 20px", cursor: "pointer", fontSize: 14,
              background: activeTab === key ? "#334155" : "transparent",
              borderLeft: activeTab === key ? "3px solid #2563eb" : "3px solid transparent",
              color: activeTab === key ? "#e2e8f0" : "#94a3b8",
            }}>
            {label}
          </div>
        ))}
      </div>

      {/* MAIN CONTENT */}
      <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
        {activeTab === "dashboard" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h1 style={{ margin: 0 }}>📊 AI Earning Machine Dashboard</h1>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={runCycle} style={btnStyle}>▶ Run Cycle</button>
                <button onClick={runAll} style={{ ...btnStyle, background: "#7c3aed" }}>🚀 Run All</button>
              </div>
            </div>

            {/* Stats Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
              <StatCard label="Wallet Balance" value={`$${dashboard?.wallet.allocated_balance.toLocaleString()} ${dashboard?.wallet.currency}`} color="#4ade80" />
              <StatCard label="Total Revenue" value={`$${dashboard?.total_revenue.toLocaleString() ?? "0"}`} color="#60a5fa" />
              <StatCard label="Stop-Loss" value={dashboard?.stop_loss.halted ? "⚠️ HALTED" : "✅ Active"} color={dashboard?.stop_loss.halted ? "#f87171" : "#4ade80"} />
              <StatCard label="Active Strategies" value={String(dashboard?.strategies.filter((s: any) => s.enabled).length ?? 0)} color="#fbbf24" />
            </div>

            {/* Strategy Cards */}
            <h2 style={{ marginTop: 0 }}>AI Earning Strategies</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
              {strategies.map((s) => (
                <div key={s.id} style={{ background: "#1e293b", borderRadius: 12, padding: 16, border: `1px solid ${s.enabled ? riskColor(s.risk_level) : "#334155"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <strong style={{ fontSize: 15 }}>{s.display_name}</strong>
                      <div style={{ fontSize: 11, color: riskColor(s.risk_level), marginTop: 2 }}>
                        Risk: {s.risk_level.toUpperCase()}
                      </div>
                    </div>
                    <button
                      onClick={() => toggleStrategy(s.name, !s.enabled)}
                      style={{
                        padding: "6px 14px", borderRadius: 6, cursor: "pointer", border: "none",
                        background: s.enabled ? "#dc2626" : "#16a34a", color: "#fff",
                        fontSize: 12, fontWeight: 600,
                      }}>
                      {s.enabled ? "Disable" : "Enable"}
                    </button>
                  </div>
                  <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 12, color: "#94a3b8" }}>
                    <span>🎯 Target: ${s.daily_profit_target}</span>
                    <span>🛑 Limit: ${s.daily_loss_limit}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "logs" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h1 style={{ margin: 0 }}>📜 Agent Activity Logs</h1>
              <button onClick={refreshAll} style={btnStyle}>🔄 Refresh</button>
            </div>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 0 }}>
              Live feed — agent kya kar raha hai, sab yahan dekhein (har 10 second mein auto-refresh)
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {logs.map((log, i) => (
                <div key={i} style={{
                  background: "#1e293b", borderRadius: 10, padding: "12px 16px",
                  borderLeft: `4px solid ${logColor(log.level || "")}`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>
                      {logIcon(log.type)} {log.action}
                    </span>
                    <span style={{ fontSize: 11, color: "#64748b" }}>{formatTime(log.time)}</span>
                  </div>
                  {log.detail && <div style={{ fontSize: 13, color: "#cbd5e1", marginTop: 4 }}>{log.detail}</div>}
                  {log.result && <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{log.result}</div>}
                  {(log.revenue ?? 0) > 0 && (
                    <div style={{ fontSize: 12, color: "#4ade80", marginTop: 2 }}>💰 +${log.revenue}</div>
                  )}
                  {(log.profit ?? 0) > 0 && (
                    <div style={{ fontSize: 12, color: "#4ade80", marginTop: 2 }}>📈 +${log.profit} profit</div>
                  )}
                </div>
              ))}
              {logs.length === 0 && (
                <div style={{ textAlign: "center", color: "#64748b", padding: 40 }}>
                  <p>Abhi koi activity nahi hai. Dashboard se "Run Cycle" dabao!</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* OTHER TABS */}
        {activeTab === "finances" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <Panel title="Deposit Money">
                <div style={{ display: "flex", gap: 8 }}>
                  <input value={depAmt} onChange={(e) => setDepAmt(e.target.value)} style={inputStyle} placeholder="Amount" />
                  <button onClick={doDeposit} style={btnStyle}>Deposit {balance?.currency}</button>
                </div>
              </Panel>
              <Panel title="Create Deal">
                <input value={dealCust} onChange={(e) => setDealCust(e.target.value)} style={{ ...inputStyle, marginBottom: 6 }} placeholder="Customer" />
                <input value={dealTitle} onChange={(e) => setDealTitle(e.target.value)} style={{ ...inputStyle, marginBottom: 6 }} placeholder="Title" />
                <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                  <input value={dealAmt} onChange={(e) => setDealAmt(e.target.value)} style={inputStyle} placeholder="Amount" />
                  <input value={dealCost} onChange={(e) => setDealCost(e.target.value)} style={inputStyle} placeholder="Cost" />
                </div>
                <button onClick={doDeal} style={btnStyle}>Create Deal</button>
              </Panel>
            </div>

            <div style={{ background: "#1e293b", borderRadius: 16, padding: 16 }}>
              <h3>Money History</h3>
              <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead><tr style={{ color: "#94a3b8" }}><th style={thStyle}>Type</th><th style={thStyle}>Amount</th><th style={thStyle}>Balance</th><th style={thStyle}>Detail</th></tr></thead>
                <tbody>
                  {ledger.slice(0, 15).map((l: any) => (
                    <tr key={l.id} style={{ borderTop: "1px solid #334155" }}>
                      <td style={tdStyle}><span style={{ color: l.direction === "credit" ? "#4ade80" : "#f87171" }}>{l.category}</span></td>
                      <td style={tdStyle}>{l.direction === "credit" ? "+" : "-"}{l.amount}</td>
                      <td style={tdStyle}>{l.balance_after}</td>
                      <td style={tdStyle}>{l.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ background: "#1e293b", borderRadius: 16, padding: 16 }}>
              <h3>Open Deals</h3>
              {deals.filter((d: any) => d.status !== "settled").map((d: any) => (
                <div key={d.id} style={{ borderTop: "1px solid #334155", padding: "8px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span><strong>{d.title}</strong> — {d.customer} (${d.amount})</span>
                  <button onClick={() => confirmPayment(d.id)} style={{ ...btnStyle, fontSize: 12 }}>Payment Received</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Chat always visible at bottom */}
        <div style={{ marginTop: 24, background: "#1e293b", borderRadius: 16, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>💬 Agent Chat</h3>
          <div style={{ maxHeight: 200, overflowY: "auto", marginBottom: 12 }}>
            {chatLog.map((c, i) => (
              <div key={i} style={{ margin: "6px 0", textAlign: c.role === "user" ? "right" : "left" }}>
                <span style={{ background: c.role === "user" ? "#2563eb" : "#334155", padding: "6px 10px", borderRadius: 10, display: "inline-block", maxWidth: "80%", fontSize: 13 }}>
                  {c.text}
                </span>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doChat()}
              placeholder="Ask the AI agent..." style={{ ...inputStyle, flex: 1 }} />
            <button onClick={doChat} style={btnStyle}>Send</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Shared styles
const inputStyle: any = { background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0", padding: 10, borderRadius: 8, width: "100%" };
const btnStyle: any = { background: "#2563eb", color: "#fff", border: "none", padding: "10px 16px", borderRadius: 8, cursor: "pointer", fontWeight: 600, whiteSpace: "nowrap" };
const thStyle: any = { textAlign: "left", padding: "6px" };
const tdStyle: any = { padding: "6px" };

function StatCard({ label, value, color }: any) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 12, padding: 16, borderLeft: `4px solid ${color}` }}>
      <div style={{ color: "#94a3b8", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color }}>{value}</div>
    </div>
  );
}

function Panel({ title, children }: any) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 16, padding: 16 }}>
      <h3 style={{ marginTop: 0, fontSize: 15 }}>{title}</h3>
      {children}
    </div>
  );
}