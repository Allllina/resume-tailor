/**
 * use-demo-sequence — the deterministic, loopable timeline that drives the
 * /demo product walkthrough.
 *
 * It's a small phase state machine advanced by setTimeout chains (no random,
 * no rAF jitter, no network). Each phase exposes derived UI state (camera
 * target, composer text, chat messages, whether the diagnosis view is mounted
 * + how far it's auto-scrolled) so the route can render purely from this hook.
 *
 * Beats (matches the approved beat sheet):
 *   0 inbox_hold      — full inbox, camera scale 1, hold ~1.5s
 *   1 zoom_composer   — camera zooms into the composer (~600ms)
 *   2 typing          — typewriter the JD into the composer (~30ms/char)
 *   3 sending         — user bubble shown, agent "thinking" (~1s)
 *   4 streaming       — agent reply streams token-by-token + attaches draft
 *   5 zoom_out        — camera zooms back to full (~600ms)
 *   6 diagnosis       — cross-fade to run-detail diagnosis, auto-scroll pan
 *   7 diagnosis_hold  — hold on diagnosis (~2s), then loop
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { DEMO_AGENT_REPLY, DEMO_JD_TEXT } from "./demo-data";

export interface DemoDataParams {
  jdText: string;
  agentReply: string;
}

export type DemoPhase =
  | "inbox_hold"
  | "zoom_composer"
  | "typing"
  | "sending"
  | "streaming"
  | "zoom_out"
  | "diagnosis"
  | "diagnosis_hold";

export interface CameraTarget {
  scale: number;
  /** translate in % of the camera stage (applied before scale via transform-origin center). */
  x: number;
  y: number;
}

export interface DemoState {
  phase: DemoPhase;
  /** Camera transform target for the inbox stage. */
  camera: CameraTarget;
  /** Text currently in the composer textarea (grows during `typing`). */
  composerText: string;
  /** Whether the user JD bubble has been "sent" into the thread. */
  userSent: boolean;
  /** Whether the agent "thinking" indicator is visible. */
  thinking: boolean;
  /** Streamed portion of the agent reply (grows during `streaming`). */
  agentReply: string;
  /** Whether the attached-draft card is shown under the agent reply. */
  draftAttached: boolean;
  /** Whether the hero run has joined the dense left list. */
  heroInList: boolean;
  /** Whether the diagnosis view is mounted (cross-fade in on `diagnosis`). */
  showDiagnosis: boolean;
  /** Diagnosis auto-scroll progress, 0..1 (drives a translateY pan). */
  diagnosisScroll: number;
  /** True while paused (controls). */
  paused: boolean;
}

// Camera presets. The composer sits in the lower-right of the inbox, so we
// zoom in and translate up-left to bring it to centre. transform-origin is
// the stage centre, so positive x/y push content right/down.
const CAM_FULL: CameraTarget = { scale: 1, x: 0, y: 0 };
const CAM_COMPOSER: CameraTarget = { scale: 1.7, x: -22, y: -26 };

// Phase durations (ms). Total ≈ 29s, comfortably in the 25–35s window.
const D = {
  inbox_hold: 1500,
  zoom_composer: 700,
  // typing handled per-char (jdText.length * type_ms)
  type_ms: 38,
  type_tail: 350, // pause after typing finishes, before send
  sending: 1100, // thinking indicator
  // streaming handled per-char (agentReply.length * stream_ms)
  stream_ms: 22,
  stream_tail: 900, // hold after stream completes
  zoom_out: 700,
  zoom_out_tail: 250,
  // diagnosis auto-scroll handled per-frame
  diagnosis_scroll: 7000,
  diagnosis_hold: 2200,
} as const;

const INITIAL: DemoState = {
  phase: "inbox_hold",
  camera: CAM_FULL,
  composerText: "",
  userSent: false,
  thinking: false,
  agentReply: "",
  draftAttached: false,
  heroInList: false,
  showDiagnosis: false,
  diagnosisScroll: 0,
  paused: false,
};

export function useDemoSequence(
  autoStart = true,
  data: DemoDataParams = { jdText: DEMO_JD_TEXT, agentReply: DEMO_AGENT_REPLY },
) {
  const dataRef = useRef(data);
  dataRef.current = data; // keep in sync each render without re-running effects

  const [state, setState] = useState<DemoState>(INITIAL);
  const timers = useRef<number[]>([]);
  const raf = useRef<number | null>(null);
  const runningRef = useRef(false);

  const clearAll = useCallback(() => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
    if (raf.current != null) {
      window.cancelAnimationFrame(raf.current);
      raf.current = null;
    }
  }, []);

  const at = useCallback((ms: number, fn: () => void) => {
    const id = window.setTimeout(fn, ms);
    timers.current.push(id);
  }, []);

  // A self-rescheduling rAF ramp from 0..1 over `durationMs`, calling onProgress
  // each frame and onDone at the end. Used for the typewriter, token stream and
  // diagnosis pan so they read smooth + are tied to wall-clock (deterministic
  // given a fixed start), independent of frame rate.
  const ramp = useCallback(
    (durationMs: number, onProgress: (p: number) => void, onDone: () => void) => {
      const start = performance.now();
      const step = () => {
        const p = Math.min(1, (performance.now() - start) / durationMs);
        onProgress(p);
        if (p < 1) {
          raf.current = window.requestAnimationFrame(step);
        } else {
          raf.current = null;
          onDone();
        }
      };
      raf.current = window.requestAnimationFrame(step);
    },
    [],
  );

  const run = useCallback(() => {
    clearAll();
    runningRef.current = true;
    setState({ ...INITIAL });

    // Beat 1: hold on full inbox, then zoom into composer.
    at(D.inbox_hold, () => {
      setState((s) => ({ ...s, phase: "zoom_composer", camera: CAM_COMPOSER }));

      // Beat 2: typewriter the JD into the composer.
      at(D.zoom_composer, () => {
        setState((s) => ({ ...s, phase: "typing" }));
        const { jdText, agentReply } = dataRef.current;
        const typingTotal = jdText.length * D.type_ms;
        const streamTotal = agentReply.length * D.stream_ms;
        ramp(
          typingTotal,
          (p) => {
            const n = Math.round(p * jdText.length);
            setState((s) => ({ ...s, composerText: jdText.slice(0, n) }));
          },
          () => {
            setState((s) => ({ ...s, composerText: jdText }));

            // Beat 3: send — push user bubble, clear composer, show thinking,
            // and immediately zoom back out so the inbox is visible during streaming.
            at(D.type_tail, () => {
              setState((s) => ({
                ...s,
                phase: "sending",
                userSent: true,
                composerText: "",
                thinking: true,
                camera: CAM_FULL,
              }));

              // Beat 4: agent reply streams token-by-token.
              at(D.sending, () => {
                setState((s) => ({ ...s, phase: "streaming", thinking: false }));
                ramp(
                  streamTotal,
                  (p) => {
                    const n = Math.round(p * agentReply.length);
                    setState((s) => ({ ...s, agentReply: agentReply.slice(0, n) }));
                  },
                  () => {
                    setState((s) => ({
                      ...s,
                      agentReply: agentReply,
                      draftAttached: true,
                      heroInList: true,
                    }));

                    // Beat 5 (removed — camera already at CAM_FULL since send).
                    // Beat 6: cross-fade to diagnosis after a brief hold.
                    at(D.stream_tail, () => {
                      setState((s) => ({ ...s, phase: "zoom_out" }));

                      at(D.zoom_out_tail, () => {
                        setState((s) => ({ ...s, phase: "diagnosis", showDiagnosis: true }));
                        ramp(
                          D.diagnosis_scroll,
                          (p) => setState((s) => ({ ...s, diagnosisScroll: p })),
                          () => {
                            setState((s) => ({ ...s, phase: "diagnosis_hold", diagnosisScroll: 1 }));

                            // Beat 7: hold, then loop.
                            at(D.diagnosis_hold, () => {
                              if (runningRef.current) run();
                            });
                          },
                        );
                      });
                    });
                  },
                );
              });
            });
          },
        );
      });
    });
  }, [at, clearAll, ramp]);

  const restart = useCallback(() => {
    run();
  }, [run]);

  const pause = useCallback(() => {
    runningRef.current = false;
    clearAll();
    setState((s) => ({ ...s, paused: true }));
  }, [clearAll]);

  const resume = useCallback(() => {
    setState((s) => ({ ...s, paused: false }));
    run();
  }, [run]);

  useEffect(() => {
    if (autoStart) run();
    return () => {
      runningRef.current = false;
      clearAll();
    };
    // run/clearAll are stable (useCallback); we only want this on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { state, restart, pause, resume, isPaused: state.paused };
}
