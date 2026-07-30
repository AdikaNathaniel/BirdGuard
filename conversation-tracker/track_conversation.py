"""Export Claude Code session transcript(s) for this project into a readable log.

Claude Code stores each session as a JSONL file under:
    ~/.claude/projects/<sanitized-project-path>/<session-id>.jsonl

This script finds that folder, reads the transcript(s), and writes a clean
markdown log of the conversation (user messages, assistant replies, and the
commands the assistant ran) to conversation_log.md in this folder.

Usage:
    python track_conversation.py            # log the current/latest session only
    python track_conversation.py --all       # log every saved session, oldest first
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def sanitize_cwd(cwd: str) -> str:
    return (cwd[0].lower() + cwd[1:]).replace(":", "-").replace("\\", "-").replace("/", "-")


def find_session_dir(project_root: Path) -> Path:
    folder = sanitize_cwd(str(project_root))
    base = Path.home() / ".claude" / "projects" / folder
    if not base.exists():
        raise SystemExit(f"No Claude Code session directory found at {base}")
    return base


def list_transcripts(session_dir: Path, all_sessions: bool):
    jsonl_files = sorted(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not jsonl_files:
        raise SystemExit(f"No .jsonl transcripts found in {session_dir}")
    return jsonl_files if all_sessions else [jsonl_files[-1]]


def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        btype = block.get("type")
        if btype == "text":
            parts.append(block.get("text", ""))
        elif btype == "tool_use":
            name = block.get("name", "tool")
            inp = block.get("input", {}) or {}
            cmd = inp.get("command") or inp.get("pattern") or inp.get("file_path") or ""
            parts.append(f"[ran {name}: {cmd}]" if cmd else f"[ran {name}]")
    return "\n".join(p for p in parts if p)


def build_log(transcript_path: Path) -> str:
    lines = [f"## Session: {transcript_path.stem}\n"]
    with open(transcript_path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue

            etype = entry.get("type")
            if etype not in ("user", "assistant"):
                continue

            text = extract_text(entry.get("message", {}).get("content", ""))
            if not text.strip():
                continue

            ts = entry.get("timestamp", "")
            speaker = "USER" if etype == "user" else "ASSISTANT"
            lines.append(f"### [{ts}] {speaker}\n{text}\n")

    return "\n".join(lines)


def main():
    all_sessions = "--all" in sys.argv
    project_root = Path(__file__).resolve().parent.parent
    session_dir = find_session_dir(project_root)
    transcripts = list_transcripts(session_dir, all_sessions)

    out_path = Path(__file__).resolve().parent / "conversation_log.md"
    header = (
        f"# BirdGuard Conversation Log\n"
        f"Generated: {datetime.now().isoformat()}\n"
        f"Sessions included: {len(transcripts)}\n\n"
    )
    body = "\n\n".join(build_log(t) for t in transcripts)
    out_path.write_text(header + body, encoding="utf-8")
    print(f"Wrote log to {out_path}")


if __name__ == "__main__":
    main()
