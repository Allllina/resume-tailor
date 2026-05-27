import { useState } from "react";
import { Github, Globe, Info, KeyRound, Lock } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";

type ModalKey = null | "connections" | "sources" | "privacy" | "about";

export function AppMenu() {
  const [modal, setModal] = useState<ModalKey>(null);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="text-xs text-muted-foreground transition hover:text-foreground"
            aria-label="Menu"
          >
            ⋯
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>Settings</DropdownMenuLabel>
          <DropdownMenuItem onClick={() => setModal("connections")}>
            <KeyRound className="h-3.5 w-3.5" />
            Connections
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setModal("sources")}>
            <Globe className="h-3.5 w-3.5" />
            Auto-search sources
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setModal("privacy")}>
            <Lock className="h-3.5 w-3.5" />
            Privacy
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setModal("about")}>
            <Info className="h-3.5 w-3.5" />
            About
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={modal !== null} onOpenChange={(o) => !o && setModal(null)}>
        <DialogContent className="max-w-md">
          {modal === "connections" ? <Connections /> : null}
          {modal === "sources" ? <Sources /> : null}
          {modal === "privacy" ? <Privacy /> : null}
          {modal === "about" ? <About /> : null}
        </DialogContent>
      </Dialog>
    </>
  );
}

/* ------------------------------ Connections ------------------------------ */

function Connections() {
  return (
    <>
      <DialogHeader>
        <DialogTitle>Connections</DialogTitle>
        <DialogDescription>The LLM I run on. Stored on your machine only.</DialogDescription>
      </DialogHeader>
      <div className="mt-4 space-y-4">
        <div>
          <label className="text-xs font-medium text-foreground">Provider</label>
          <select
            defaultValue="anthropic"
            className="mt-1.5 h-10 w-full rounded-lg border border-border bg-card px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/40"
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="custom">Custom (OpenAI-compatible)</option>
          </select>
        </div>

        <div>
          <label className="text-xs font-medium text-foreground">API key</label>
          <input
            type="password"
            placeholder="sk-ant-…"
            defaultValue="sk-ant-•••••••••••••••••"
            className="mt-1.5 h-10 w-full rounded-lg border border-border bg-card px-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring/40"
          />
        </div>

        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Advanced
          </summary>
          <div className="mt-2 space-y-2">
            <label className="text-xs font-medium text-foreground">Base URL override</label>
            <input
              type="text"
              placeholder="https://api.anthropic.com"
              className="h-10 w-full rounded-lg border border-border bg-card px-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring/40"
            />
          </div>
        </details>

        <div className="flex justify-end gap-2 pt-2">
          <button className="h-9 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20">
            Verify
          </button>
          <button className="h-9 rounded-md bg-foreground px-3 text-xs font-medium text-background transition hover:opacity-90">
            Save
          </button>
        </div>
      </div>
    </>
  );
}

/* -------------------------------- Sources -------------------------------- */

function Sources() {
  const [docs, setDocs] = useState([
    "https://docs.qq.com/sheet/internships-spring",
    "https://docs.qq.com/doc/referral-q1",
  ]);
  const [draft, setDraft] = useState("");
  const [autoScan, setAutoScan] = useState(true);

  const add = () => {
    const v = draft.trim();
    if (!v) return;
    if (!docs.includes(v)) setDocs((prev) => [...prev, v]);
    setDraft("");
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>Auto-search sources</DialogTitle>
        <DialogDescription>
          Documents I poll for new JDs. Drop a 腾讯文档 URL or any plain markdown / google doc link.
        </DialogDescription>
      </DialogHeader>

      <div className="mt-4 space-y-4">
        <div>
          <label className="text-xs font-medium text-foreground">Tracked documents</label>
          <ul className="mt-1.5 space-y-1.5">
            {docs.map((d) => (
              <li
                key={d}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2"
              >
                <span className="truncate font-mono text-xs text-foreground/85">{d}</span>
                <button
                  onClick={() => setDocs((prev) => prev.filter((x) => x !== d))}
                  className="text-muted-foreground transition hover:text-foreground"
                  aria-label={`Remove ${d}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-2 flex gap-2">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  add();
                }
              }}
              placeholder="https://…"
              className="h-9 flex-1 rounded-md border border-border bg-card px-3 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-ring/40"
            />
            <button
              onClick={add}
              className="h-9 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
            >
              Add
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card px-3 py-2.5">
          <div>
            <p className="text-sm font-medium text-foreground">Auto-scan every 30 min</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Off means I only check when you open the inbox.
            </p>
          </div>
          <Switch checked={autoScan} onCheckedChange={setAutoScan} />
        </div>
      </div>
    </>
  );
}

/* -------------------------------- Privacy -------------------------------- */

function Privacy() {
  const [redact, setRedact] = useState(true);

  return (
    <>
      <DialogHeader>
        <DialogTitle>Privacy</DialogTitle>
        <DialogDescription>What I store, what I can send, and how to wipe it.</DialogDescription>
      </DialogHeader>

      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card px-3 py-2.5">
          <div>
            <p className="text-sm font-medium text-foreground">Redact PII before sending</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Names, emails, phone numbers swapped with placeholders before the model sees them.
            </p>
          </div>
          <Switch checked={redact} onCheckedChange={setRedact} />
        </div>

        <button className="h-10 w-full rounded-lg border border-border bg-card text-sm font-medium transition hover:border-foreground/20">
          Export all data
        </button>
        <button className="h-10 w-full rounded-lg border border-error/40 bg-card text-sm font-medium text-error transition hover:bg-error/5">
          Delete everything
        </button>
        <p className="pt-1 text-[11px] leading-relaxed text-muted-foreground">
          Delete is irreversible — drafts, JDs, experience bank, all gone. You'll start from /setup
          again.
        </p>
      </div>
    </>
  );
}

/* --------------------------------- About --------------------------------- */

function About() {
  return (
    <>
      <DialogHeader>
        <DialogTitle>Resume Tailor</DialogTitle>
        <DialogDescription>v0.4 · 2026-05</DialogDescription>
      </DialogHeader>

      <div className="mt-4 space-y-3 text-sm">
        <p className="leading-relaxed text-foreground/85">
          AI-native autopilot for tailoring resumes against any JD. You drop a job description; I
          read it, pick from your experience bank, and rewrite the parts that matter. You always
          review and submit.
        </p>
        <a
          href="https://github.com/Allllina/ai-assistant"
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
        >
          <Github className="h-3.5 w-3.5" />
          GitHub
        </a>
      </div>
    </>
  );
}
