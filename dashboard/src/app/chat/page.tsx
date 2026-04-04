"use client";
import { useState, useRef, useEffect } from "react";
import { Send, AlertTriangle, Megaphone, BookOpen, Trash2 } from "lucide-react";
import Card from "@/components/shared/Card";
import { apiPost } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: ChatResponse["sources"];
  latency_ms?: number;
  type?: "chat" | "explain" | "announcement";
}

const HISTORY_KEY = "skyops-chat-history";
const MAX_HISTORY = 20;

const SCENARIOS = [
  {
    label: "시나리오 1: 기상 지연",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    action: "announcement" as const,
    data: { flight_number: "KE081", delay_type: "weather", delay_minutes: 38, details: "인천공항 활주로 34L 강풍 45노트, B777 이륙 제한 초과" },
    preChat: "KE081편의 출발 지연이 예측됩니다. 현재 인천공항 활주로 34L에 45노트 강풍이 감지되었으며, 이는 B777 이륙 제한 기준(40노트)을 초과합니다. 예측 지연 시간: 38분. 승객 안내방송 발령을 권고합니다.",
  },
  {
    label: "시나리오 2: 이상 비행",
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    action: "explain" as const,
    data: { callsign: "KAL1133", anomaly_type: "ALTITUDE_SPIKE", severity: "HIGH", description: "고도 급변 감지: 427m 변화 / 23초", altitude_m: 8500, velocity_m_s: 240 },
  },
  {
    label: "시나리오 3: FAA 규정 QA",
    icon: <BookOpen className="w-3.5 h-3.5" />,
    action: "chat" as const,
    question: "비상 선언 항공기(7700 Squawk)에 대한 관제 우선 처리 절차를 설명해주세요.",
  },
];

function loadHistory(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveHistory(msgs: Message[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(msgs.slice(-MAX_HISTORY)));
  } catch {}
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [activeTab, setActiveTab] = useState<"chat" | "announcement">("chat");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Announcement form
  const [annForm, setAnnForm] = useState({ flight_number: "", delay_type: "weather", delay_minutes: 30, details: "" });
  const [announcement, setAnnouncement] = useState("");
  const [annLoading, setAnnLoading] = useState(false);

  useEffect(() => { setMessages(loadHistory()); }, []);
  useEffect(() => { saveHistory(messages); }, [messages]);
  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  const addMsg = (msg: Message) => setMessages((prev) => [...prev, msg].slice(-MAX_HISTORY));

  const sendChat = async (question?: string) => {
    const q = question || input.trim();
    if (!q || loading) return;
    if (!question) setInput("");
    addMsg({ role: "user", content: q, type: "chat" });
    setLoading(true);
    try {
      const res = await apiPost<ChatResponse>("/chat", { question: q, use_rag: useRag });
      addMsg({ role: "assistant", content: res.answer, sources: res.sources, latency_ms: res.latency_ms, type: "chat" });
    } catch {
      addMsg({ role: "assistant", content: "서버 연결 실패. FastAPI + vLLM이 실행 중인지 확인하세요.", type: "chat" });
    } finally { setLoading(false); }
  };

  const explainAnomaly = async (data: typeof SCENARIOS[1]["data"]) => {
    setLoading(true);
    addMsg({ role: "system", content: `🚨 이상 탐지: ${(data as {callsign:string}).callsign} — ${(data as {description:string}).description}`, type: "explain" });
    try {
      const res = await apiPost<{ explanation: string; latency_ms: number }>("/explain/anomaly", data);
      addMsg({ role: "assistant", content: res.explanation, latency_ms: res.latency_ms, type: "explain" });
    } catch {
      addMsg({ role: "assistant", content: "이상 탐지 설명 생성 실패.", type: "explain" });
    } finally { setLoading(false); }
  };

  const generateAnnouncement = async (data: { flight_number: string; delay_type: string; delay_minutes: number; details: string }) => {
    setAnnLoading(true);
    try {
      const res = await apiPost<{ announcement: string; latency_ms: number }>("/generate/announcement", data);
      setAnnouncement(res.announcement);
      addMsg({ role: "system", content: `📢 승객 안내문 생성: ${data.flight_number} (${data.delay_type}, ${data.delay_minutes}분 지연)`, type: "announcement" });
      addMsg({ role: "assistant", content: res.announcement, latency_ms: res.latency_ms, type: "announcement" });
    } catch {
      setAnnouncement("안내문 생성 실패.");
    } finally { setAnnLoading(false); }
  };

  const runScenario = async (s: typeof SCENARIOS[number]) => {
    if (s.action === "announcement") {
      if (s.preChat) addMsg({ role: "system", content: `⚠️ ${s.preChat}`, type: "explain" });
      await generateAnnouncement(s.data as { flight_number: string; delay_type: string; delay_minutes: number; details: string });
    } else if (s.action === "explain") {
      await explainAnomaly(s.data as typeof SCENARIOS[1]["data"]);
    } else {
      await sendChat((s as typeof SCENARIOS[2]).question);
    }
  };

  const clearHistory = () => { setMessages([]); localStorage.removeItem(HISTORY_KEY); };

  const msgColor = (msg: Message) => {
    if (msg.role === "system") return "bg-amber-500/10 text-amber-200 border border-amber-500/20";
    if (msg.role === "user") return "bg-sky-500/20 text-sky-100";
    return "bg-slate-800 text-slate-200";
  };

  return (
    <div className="h-[calc(100vh-3rem)] flex gap-4">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">AI 관제 어시스턴트</h1>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} className="rounded" />
              <span className="text-slate-400">RAG</span>
            </label>
            <button onClick={clearHistory} className="text-slate-500 hover:text-slate-300 p-1" title="대화 초기화">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        <Card className="flex-1 flex flex-col p-0 overflow-hidden">
          <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-3">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 text-sm space-y-4">
                <p>항공 관제 관련 질문을 입력하거나 시나리오를 선택하세요</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {SCENARIOS.map((s, i) => (
                    <button key={i} onClick={() => runScenario(s)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition-colors">
                      {s.icon} {s.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-xl px-4 py-3 ${msgColor(msg)}`}>
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-slate-700 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase">참조 문서</span>
                      {msg.sources.map((s, j) => (
                        <div key={j} className="text-[11px] text-slate-400">{s.source} — {s.section}</div>
                      ))}
                    </div>
                  )}
                  {msg.latency_ms && <div className="text-[10px] text-slate-600 mt-1">{msg.latency_ms.toFixed(0)}ms</div>}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-800 rounded-xl px-4 py-3 text-sm text-slate-400 animate-pulse">응답 생성 중...</div>
              </div>
            )}
          </div>

          <div className="border-t border-slate-700 p-4">
            <div className="flex gap-2 mb-2">
              {messages.length > 0 && SCENARIOS.map((s, i) => (
                <button key={i} onClick={() => runScenario(s)} disabled={loading}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-400 disabled:opacity-50">
                  {s.icon} {s.label.split(": ")[1]}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input value={input} onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendChat()}
                placeholder="항공 관제 질문을 입력하세요..."
                className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-sky-500" />
              <button onClick={() => sendChat()} disabled={loading || !input.trim()}
                className="bg-sky-500 hover:bg-sky-600 disabled:bg-slate-700 text-white px-4 py-2.5 rounded-lg transition-colors">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </Card>
      </div>

      {/* Side panel */}
      <div className="w-80 flex flex-col gap-4 flex-shrink-0">
        <div className="flex rounded-lg bg-slate-800 p-0.5">
          {(["chat", "announcement"] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 text-xs font-semibold rounded-md transition-colors ${
                activeTab === tab ? "bg-sky-500/20 text-sky-400" : "text-slate-400 hover:text-slate-200"
              }`}>
              {tab === "chat" ? "빠른 질문" : "승객 안내문"}
            </button>
          ))}
        </div>

        {activeTab === "chat" ? (
          <Card title="빠른 질문 템플릿" className="flex-1 overflow-y-auto">
            <div className="space-y-2">
              {[
                "Go-Around 절차를 설명해주세요.",
                "NOTAM 확인 절차는 무엇인가요?",
                "비상 착륙 시 관제사 대응 절차는?",
                "Wind Shear 경보 시 조치 사항은?",
                "ILS 접근 중 항공기 간격 기준은?",
                "항공기 연료 비상 선언 기준은?",
              ].map((q, i) => (
                <button key={i} onClick={() => sendChat(q)} disabled={loading}
                  className="w-full text-left px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-700 text-xs text-slate-300 disabled:opacity-50 transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </Card>
        ) : (
          <Card title="승객 안내문 생성" className="flex-1 overflow-y-auto">
            <div className="space-y-3">
              <label className="space-y-1">
                <span className="text-xs text-slate-400">항공편</span>
                <input value={annForm.flight_number} onChange={(e) => setAnnForm((p) => ({ ...p, flight_number: e.target.value }))}
                  placeholder="예: KE081" className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm" />
              </label>
              <label className="space-y-1">
                <span className="text-xs text-slate-400">지연 사유</span>
                <select value={annForm.delay_type} onChange={(e) => setAnnForm((p) => ({ ...p, delay_type: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm">
                  <option value="weather">기상 악화</option>
                  <option value="maintenance">기체 정비</option>
                  <option value="traffic">항공 교통 혼잡</option>
                  <option value="crew">승무원 사유</option>
                  <option value="other">기타</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-xs text-slate-400">예상 지연 (분)</span>
                <input type="number" value={annForm.delay_minutes} onChange={(e) => setAnnForm((p) => ({ ...p, delay_minutes: +e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm" />
              </label>
              <label className="space-y-1">
                <span className="text-xs text-slate-400">추가 정보</span>
                <textarea value={annForm.details} onChange={(e) => setAnnForm((p) => ({ ...p, details: e.target.value }))}
                  rows={2} placeholder="선택 사항" className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm resize-none" />
              </label>
              <button onClick={() => generateAnnouncement(annForm)} disabled={annLoading || !annForm.flight_number}
                className="w-full bg-sky-500 hover:bg-sky-600 disabled:bg-slate-600 text-white font-semibold py-2 rounded-lg text-sm flex items-center justify-center gap-2">
                <Megaphone className="w-4 h-4" /> {annLoading ? "생성 중..." : "안내문 생성"}
              </button>
              {announcement && (
                <div className="bg-slate-800/50 rounded-lg p-3 text-xs text-slate-300 whitespace-pre-wrap mt-2 border border-slate-700">
                  {announcement}
                </div>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
