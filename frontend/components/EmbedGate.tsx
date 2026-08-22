"use client";

import { useEffect, useState } from "react";
import { targetOrigin } from "@/lib/embed";

// El asistente NO debe poder abrirse suelto (por ej. entrando directo a
// http://localhost:3000). La unica forma valida de abrirlo es embebido dentro de
// CostSeg (C#) con un usuario ya logueado.
//
// Como se logra: al montar, el chatbot le pide a su ventana padre una senal de
// desbloqueo ("costseg:unlock"). Esa senal solo la emite la app de CostSeg, y
// CostSeg solo carga ese puente cuando el usuario esta autenticado (para llegar
// al formulario hay que estar logueado). Entonces:
//   - Abierto suelto (sin ventana padre)            -> queda BLOQUEADO.
//   - Embebido pero sin login / sin CostSeg detras  -> nunca llega el unlock -> BLOQUEADO.
//   - Embebido dentro de CostSeg logueado           -> llega el unlock -> se ABRE.
//
// Nota de seguridad: esto impide el uso normal fuera de CostSeg. Para blindaje
// fuerte (que nadie falsifique el mensaje desde otra pagina) hace falta ademas
// validar un token real en la API FastAPI; eso es un segundo paso aparte.

const UNLOCK_MESSAGE = "costseg:unlock";
const READY_MESSAGE = "rsmeans:ready";
const UNLOCK_TIMEOUT_MS = 5000;

type GateState = "checking" | "unlocked" | "locked";

export function EmbedGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<GateState>("checking");

  useEffect(() => {
    // Permite un bypass explicito solo en desarrollo local del propio chatbot,
    // si algun dia hace falta abrirlo suelto a proposito.
    if (process.env.NEXT_PUBLIC_DISABLE_EMBED_GATE === "true") {
      setState("unlocked");
      return;
    }

    // 1) No embebido => no hay ventana padre => bloqueado de una.
    if (typeof window === "undefined" || window.parent === window) {
      setState("locked");
      return;
    }

    const parentOrigin = targetOrigin();
    if (!parentOrigin) {
      // Embebido pero no sabemos quien es el padre: no confiamos, bloqueado.
      setState("locked");
      return;
    }

    let done = false;

    const onMessage = (event: MessageEvent) => {
      if (event.origin !== parentOrigin) return;
      if (!event.data || event.data.type !== UNLOCK_MESSAGE) return;
      done = true;
      window.removeEventListener("message", onMessage);
      clearInterval(pinger);
      clearTimeout(timer);
      setState("unlocked");
    };

    window.addEventListener("message", onMessage);

    // Le avisamos al padre que estamos listos y pedimos el desbloqueo. Se repite
    // por si el puente del padre se engancha un instante despues que el iframe.
    const askUnlock = () =>
      window.parent.postMessage({ type: READY_MESSAGE }, parentOrigin);
    askUnlock();
    const pinger = setInterval(askUnlock, 400);

    // Si nadie desbloquea en el plazo, queda bloqueado.
    const timer = setTimeout(() => {
      if (done) return;
      window.removeEventListener("message", onMessage);
      clearInterval(pinger);
      setState("locked");
    }, UNLOCK_TIMEOUT_MS);

    return () => {
      window.removeEventListener("message", onMessage);
      clearInterval(pinger);
      clearTimeout(timer);
    };
  }, []);

  if (state === "unlocked") return <>{children}</>;

  // Pantalla de candado (chequeando o bloqueado). Mientras chequea mostramos un
  // texto neutro para no parpadear el candado si el unlock llega rapido.
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-sm rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <rect x="4" y="11" width="16" height="9" rx="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
        </div>
        {state === "checking" ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Verificando la sesión…
          </p>
        ) : (
          <>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Acceso restringido
            </h2>
            <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">
              Este asistente solo se abre desde CostSeg. Inicia sesión en CostSeg
              y ábrelo con el botón <span className="font-medium">Ask AI</span>{" "}
              del formulario.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
