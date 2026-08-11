"use client";
import { useEffect, useState } from "react";
import { chat, login, apiGet, apiPost } from "@/lib/api";

type Balance = { allocated_balance: number; currency: string; real_money_note: string };
type LedgerItem = { id: number; direction: string; category: string; amount: number; balance_after: number; description: string; time: string };
type Notif = { id: number; title: string; body: string; level: string; time: string };
type Status = { stop_loss: { halted: boolean; reason: string }; wallet: Balance };

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [pw, setPw] = useState("");
  const [balance, setBalance] = useState<Balance | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [ledger, setLedger] = useState<LedgerItem[]>([]);
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [msg, setMsg] = useState("");
  const [chatLog, setChatLog] = useState<{ role: string; text: string }[]>([]);

  const [depAmt, setDepAmt] = useState("100");
  const [dealCust, setDealCust] = useState("");
  const [dealTitle, setDealTitle] = useState("");
  const [dealAmt, setDealAmt] = useState("100");
  const [dealCost, setDealCost] = useState("0");
  const [deals, setDeals] = useState<any[]>([]);

  async function doLogin() {
    const r = await login(pw);
    setToken(r.token);
    await refreshAll(r.token);
  }

  async function refreshAll(t: string) {
    try {
      const [b, s, l, n, d] = await Promise.all([
        apiGet("/api/balance", t),
        apiGet("/owner/status", t),
        apiGet("/api/ledger", t),
        apiGet("/api/notifications", t),
        apiGet("/api/deals", t),
      ]);
      setBalance(b);
      setStatus(s);
      setLedger(l);
      setNotifs(n);
      setDeals(d);
    } catch (e: any) {
      console.error(e);
    }
  }

  async function doChat() {
    if (!msg.trim()) return;
    setChatLog((c) => [...c, { role: "user", text: msg }]);
    setMsg("");
    const reply = await chat(msg);
    setChatLog((c) => [...c, { role: "agent", text: reply }]);
  }

  async function doDeposit() {
    await apiPost("/api/deposit", token!, { amount: parseFloat(depAmt) });
    await refreshAll(token!);
  }

  async function doDeal() {
    await apiPost("/api/deals", token!, {
      customer: dealCust, title: dealTitle,
      amount: parseFloat(dealAmt), cost: parseFloat(dealCost || "0"),
    });
    setDealCust(""); setDealTitle(""); setDealAmt("100"); setDealCost("0");
    await refreshAll(token!);
  }

  async function confirmPayment(dealId: number) {
    await apiPost("/api/deals/confirm-payment", token!, { deal_id: dealId });
    await refreshAll(token!);
  }

  if (!token) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ background: "#1e293b", padding: 32, borderRadius: 16, width: 320 }}>
          <h1 style={{ marginTop: 0 }}>Agent Experts</h1>
          <p style={{ color: "#94a3b8" }}>Enter owner password to unlock</p>
          <input value={pw} type="password" onChange={(e) => setPw(e.target.value)}
            placeholder="password" style={inputStyle} />
          <button onClick={doLogin} style={btnStyle}>Unlock</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: 16, padding: 16, minHeight: "100vh" }}>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Top cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          <Card label="Agent Balance" value={`${balance?.allocated_balance} ${balance?.currency}`} />
          <Card label="Real Money Note" value={balance?.real_money_note || "-"} />
          <Card label="Stop-Loss" value={status?.stop_loss.halted ? "HALTED" : "Active"} danger={status?.stop_loss.halted} />
          <Card label="Unread Alerts" value={String(notifs.filter((n) => !n.read).length)} />
        </div>

        {/* Chat */}
        <div style={{ background: "#1e293b", borderRadius: 16, padding: 16, flex: 1, display: "flex", flexDirection: "column" }}>
          <h2 style={{ marginTop: 0 }}>Agent Chat</h2>
          <div style={{ flex: 1, overflowY: "auto", maxHeight: 300, marginBottom: 12 }}>
            {chatLog.map((c, i) => (
              <div key={i} style={{ margin: "6px 0", textAlign: c.role === "user" ? "right" : "left" }}>
                <span style={{ background: c.role === "user" ? "#2563eb" : "#334155", padding: "6px 10px", borderRadius: 10, display: "inline-block", maxWidth: "80%" }}>
                  {c.text}
                </span>
              </div>
            ))}
            {chatLog.length === 0 && <p style={{ color: "#64748b" }}>Ask me about balance, deals, profits...</p>}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && doChat()}
              placeholder="Message agent" style={{ ...inputStyle, flex: 1 }} />
            <button onClick={doChat} style={btnStyle}>Send</button>
          </div>
        </div>

        {/* Ledger */}
        <div style={{ background: "#1e293b", borderRadius: 16, padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>Money History</h3>
          <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ color: "#94a3b8" }}>
                <th style={thStyle}>Type</th><th style={thStyle}>Amount</th>
                <th style={thStyle}>Balance</th><th style={thStyle}>Detail</th>
              </tr>
            </thead>
            <tbody>
              {ledger.slice(0, 12).map((l) => (
                <tr key={l.id} style={{ borderTop: "1px solid #334155" }}>
                  <td style={tdStyle}><span style={{ color: l.direction === "credit" ? "#4ade80" : "#f87171" }}>{l.category}</span></td>
                  <td style={tdStyle}>{l.direction === "credit" ? "+" : "-"}{l.amount}</td>
                  <td style={tdStyle}>{l.balance_after}</td>
                  <td style={tdStyle}>{l.description}</td>
                </tr>
              ))}
              {ledger.length === 0 && <tr><td colSpan={4} style={{ color: "#64748b", padding: 12 }}>No transactions yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* Right panel: actions */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

        <Panel title="Deposit Money">
          <div style={{ display: "flex", gap: 8 }}>
            <input value={depAmt} onChange={(e) => setDepAmt(e.target.value)} style={inputStyle}
              placeholder="amount" />
            <button onClick={doDeposit} style={btnStyle}>Add {balance?.currency}</button>
          </div>
          <p style={{ color: "#64748b", fontSize: 12, marginBottom: 0 }}>
            Records money coming into agent wallet (e.g. from Payoneer).
          </p>
        </Panel>

        <Panel title="Create Customer Deal">
          <input value={dealCust} onChange={(e) => setDealCust(e.target.value)} style={{ ...inputStyle, marginBottom: 8 }} placeholder="Customer name" />
          <input value={dealTitle} onChange={(e) => setDealTitle(e.target.value)} style={{ ...inputStyle, marginBottom: 8 }} placeholder="Deal title" />
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input value={dealAmt} onChange={(e) => setDealAmt(e.target.value)} style={inputStyle} placeholder="amount" />
            <input value={dealCost} onChange={(e) => setDealCost(e.target.value)} style={inputStyle} placeholder="cost" />
          </div>
          <button onClick={doDeal} style={btnStyle}>Create Deal</button>
        </Panel>

        <Panel title="Open Deals (confirm payment)">
          {deals.filter((d) => d.status !== "settled").length === 0 && (
            <p style={{ color: "#64748b" }}>No open deals.</p>
          )}
          {deals.filter((d) => d.status !== "settled").map((d) => (
            <div key={d.id} style={{ borderTop: "1px solid #334155", padding: "8px 0" }}>
              <strong>{d.title}</strong> <span style={{ color: "#94a3b8" }}>({d.customer})</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
                <span>{d.amount} {balance?.currency}</span>
                <button onClick={() => confirmPayment(d.id)} style={{ ...btnStyle, fontSize: 12 }}>
                  Payment received
                </button>
              </div>
            </div>
          ))}
        </Panel>

        <Panel title="Alerts">
          {notifs.slice(0, 5).map((n) => (
            <div key={n.id} style={{ borderTop: "1px solid #334155", padding: "8px 0", fontSize: 13 }}>
              <strong style={{ color: n.level === "danger" ? "#f87171" : n.level === "success" ? "#4ade80" : "#94a3b8" }}>
                {n.title}
              </strong>
              <div style={{ color: "#cbd5e1" }}>{n.body}</div>
            </div>
          ))}
          {notifs.length === 0 && <p style={{ color: "#64748b" }}>No alerts.</p>}
        </Panel>
      </div>
    </div>
  );
}

const inputStyle: any = { background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0", padding: 10, borderRadius: 8, width: "100%" };
const btnStyle: any = { background: "#2563eb", color: "#fff", border: "none", padding: "10px 16px", borderRadius: 8, cursor: "pointer", fontWeight: 600, whiteSpace: "nowrap" };
const thStyle: any = { textAlign: "left", padding: "6px" };
const tdStyle: any = { padding: "6px" };

function Card({ label, value, danger }: any) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 16, padding: 16 }}>
      <div style={{ color: "#94a3b8", fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: danger ? "#f87171" : "#e2e8f0" }}>{value}</div>
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
