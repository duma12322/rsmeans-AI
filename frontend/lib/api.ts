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
  final_code: string;
  final_name: string;
  confidence: Confidence;
  fallback_used: boolean;
  clarify_questions: string[];
  session_id?: string;
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

export type AskResponse =
  | OkResponse
  | ClarifyResponse
  | SubjectResponse
  | ErrorResponse;

export interface AskRequest {
  question?: string;
  session_id?: string;
  answer?: string;
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
