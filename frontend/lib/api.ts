// Typed client for the RSMeans FastAPI backend (POST /ask).
// The backend returns a flat object discriminated by `status`.

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type Confidence = "high" | "medium" | "low";

export interface Row {
  line_number: string;
  description: string;
  unit: string;
  bare_total: number | null;
  total_op: number | null;
}

export interface DivisionCandidate {
  code: string;
  name: string;
}

export interface ItemCandidate {
  line: string;
  description: string;
  // The catalog section the item sits in, so the user knows what the code means
  // (e.g. "Material Handling") instead of guessing from a bare line number.
  leaf_name?: string;
  section?: string;
  unit?: string;
  bare_total?: number | null;
  total_op?: number | null;
}

export interface HowToAsk {
  how_to_ask: string;
  rules: string[];
  good_examples: string[];
  avoid_examples: string[];
}

// status === "ok": routing succeeded and the grid was scraped.
export interface OkResponse {
  status: "ok";
  rows: Row[];
  matched_line: Row | null;
  path: string[];
  // Same route as `path`, but each level carries its name so the UI can show
  // "23 - Electrical › 2301 - …" instead of bare codes.
  breadcrumb?: DivisionCandidate[];
  final_code: string;
  final_name: string;
  confidence: Confidence;
  fallback_used: boolean;
  clarify_questions: string[];
  session_id?: string;
  // Present on keyword-search results (mode === "search"). `total_records` is the
  // site's own hit count; when it exceeds the cap we return the first
  // `shown_records`, set `truncated`, and put an explanatory line in `notice`.
  mode?: "search";
  search_term?: string;
  total_records?: number | null;
  shown_records?: number;
  truncated?: boolean;
  notice?: string | null;
}

// status === "needs_clarification": ambiguous, candidates + follow-up questions.
export interface ClarifyResponse {
  status: "needs_clarification";
  question: string;
  message: string;
  candidates: Array<DivisionCandidate | ItemCandidate>;
  best_match: DivisionCandidate | null;
  clarify_questions: string[];
  confidence: Confidence;
  how_to_ask: HowToAsk;
  match_type?: "division" | "item";
  session_id: string;
  locked_path?: string[];
}

// status === "needs_subject": the question named nothing to price.
export interface SubjectResponse {
  status: "needs_subject";
  question: string;
  message: string;
  candidates: [];
  categories: DivisionCandidate[];
  how_to_ask: HowToAsk;
}

export interface ErrorResponse {
  status: "error";
  message: string;
}

// Frontend-only status: the backend never returns this. It's synthesized when
// the user stops an in-flight request, so the turn is kept (with a notice)
// instead of being erased.
export interface CancelledResponse {
  status: "cancelled";
  message: string;
}

export type AskResponse =
  | OkResponse
  | ClarifyResponse
  | SubjectResponse
  | ErrorResponse
  | CancelledResponse;

export interface AskRequest {
  question?: string;
  session_id?: string;
  answer?: string;
}

// Real-time variant of ask(): hits POST /ask/stream, which emits Server-Sent
// Events. Each `progress` event reports the live phase the backend is in
// ("analyzing", "opening", "login", "navigating", "scraping"); `onProgress` is
// called with it. The promise resolves with the final AskResponse.
export type Phase =
  | "analyzing"
  | "opening"
  | "login"
  | "navigating"
  | "scraping";

export async function askStream(
  payload: AskRequest,
  onProgress: (phase: Phase) => void,
  signal?: AbortSignal
): Promise<AskResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (e) {
    // Caller aborted: re-throw so the UI can drop the turn instead of showing
    // a misleading "backend unreachable" error.
    if ((e as Error)?.name === "AbortError") throw e;
    return {
      status: "error",
      message:
        "Couldn't reach the backend. Is it running at " +
        `${API_URL}? (uvicorn app.main:app)`,
    };
  }

  if (!res.ok || !res.body) {
    return { status: "error", message: `Request failed (${res.status}).` };
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final: AskResponse | null = null;

  // SSE frames are separated by a blank line; each frame has one `data:` line.
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const dataLine = frame
        .split("\n")
        .find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const raw = dataLine.slice(5).trim();
      if (!raw) continue;
      let evt: { type: string; phase?: Phase; data?: AskResponse };
      try {
        evt = JSON.parse(raw);
      } catch {
        continue;
      }
      if (evt.type === "progress" && evt.phase) onProgress(evt.phase);
      else if (evt.type === "result" && evt.data) final = evt.data;
    }
  }

  return (
    final ?? { status: "error", message: "No response from the server." }
  );
}

export async function ask(payload: AskRequest): Promise<AskResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    return {
      status: "error",
      message:
        "Couldn't reach the backend. Is it running at " +
        `${API_URL}? (uvicorn app.main:app)`,
    };
  }

  if (!res.ok) {
    // FastAPI validation errors come back as 422 with a `detail` array.
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail) && body.detail[0]?.msg)
        detail = body.detail[0].msg;
    } catch {
      /* keep default */
    }
    return { status: "error", message: detail };
  }

  return (await res.json()) as AskResponse;
}
