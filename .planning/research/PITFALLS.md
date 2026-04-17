# Pitfalls Research

**Domain:** local-first AI mail client / intelligent email sorter
**Researched:** 2026-04-17
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Treating IMAP sequence numbers as stable IDs

**What goes wrong:**
Message actions hit the wrong email after expunges, moves, reconnects, or concurrent mailbox activity. Cached state drifts from server state, leading to wrong-thread expansion, wrong bulk actions, or deleting the wrong message.

**Why it happens:**
Teams prototype against small, quiet inboxes and use message sequence numbers as if they were permanent identifiers. IMAP does not guarantee that. Sequence numbers are re-assigned; only `(mailbox, UIDVALIDITY, UID)` is stable enough for offline resync.

**How to avoid:**
- Make `(account_id, mailbox_id, uidvalidity, uid)` the canonical remote identity everywhere.
- Treat sequence numbers as temporary transport positions only.
- On mailbox select/resync, always re-check `UIDVALIDITY`; if it changed, invalidate cached UID-derived state for that mailbox.
- Make move/delete/tag/reply pipelines idempotent against UID-based identities.
- Add tests for expunge during active triage and reconnect during bulk actions.

**Warning signs:**
- “Clicked one message, another changed.”
- Duplicate or missing messages after refresh.
- Support logs show stale UIDs after reconnect.
- Bulk actions fail only on busy inboxes or multi-client setups.

**Phase to address:**
Foundation / mail data model phase, before UX polish or automation.

---

### Pitfall 2: Building thread UI on idealized email headers

**What goes wrong:**
Threads fragment, merge incorrectly, or jump around. Reply workflows become cognitively expensive because users cannot trust the conversation view.

**Why it happens:**
Real mail data is messy: `References` and `In-Reply-To` are inconsistent, missing, or malformed. Projects often assume a clean tree, skip placeholder parents, or overfit to subject-only grouping.

**How to avoid:**
- Use a proven threading approach based primarily on `References`/`In-Reply-To`, with subject fallback only as a last resort.
- Support placeholder/dummy parents so partial folders still thread sanely.
- Keep threading and sorting separate concepts in the UI.
- Persist a computed thread cache locally, but make it rebuildable from canonical message metadata.
- Add corpus tests with broken headers, forwarded mail, mailing lists, and missing parents.

**Warning signs:**
- Users collapse a thread and unrelated mail disappears.
- Reply draft opens from the wrong parent context.
- “Re:” subject matches glue unrelated messages together.
- Threading bugs appear mainly on old imported mail or multi-client mailboxes.

**Phase to address:**
Threading / conversation UX phase.

---

### Pitfall 3: Letting AI automation act before trust is earned

**What goes wrong:**
Auto-moves, junk decisions, or suggested replies feel unsafe. One bad move can make the whole AI system feel untrustworthy, even if later accuracy improves.

**Why it happens:**
Teams optimize for demo magic: autonomous triage first, explainability and review later. Email is a high-cost domain; false positives are worse than moderate under-automation.

**How to avoid:**
- Default to assistive AI first: summarize, rank, suggest, explain.
- Require confidence thresholds plus explicit user-visible reasons before any folder move automation.
- Add reversible automation: undo, audit log, “why was this moved?”, and dry-run mode.
- Start with bounded automation windows (already in scope: delayed processing, max 15 emails/account/run).
- Track precision by action type; do not use one global “AI accuracy” metric.

**Warning signs:**
- Users manually hunt folders after every sort run.
- People disable automation but keep search/reply features.
- Debugging requires reading model prompts rather than a structured decision log.
- Product discussion centers on recall while users complain about false positives.

**Phase to address:**
AI triage phase, before enabling unattended sorting by default.

---

### Pitfall 4: Blocking the client on local LLM latency

**What goes wrong:**
The app feels slow even though it is local. Opening a message, switching threads, or starting a reply stalls while the model loads or generates.

**Why it happens:**
“Local-first” gets interpreted as “do everything inline.” Local models still have model-load cost, token latency, and CPU/GPU contention. A fast mail client dies the moment basic navigation waits on inference.

**How to avoid:**
- Keep navigation, selection, search, and message rendering completely independent from LLM execution.
- Stream long AI outputs; use non-streaming only when structured output is genuinely simpler.
- Precompute low-priority summaries in background jobs, never on the critical path.
- Surface AI states explicitly: queued, generating, stale, failed, cached.
- Budget inference concurrency so indexing/search/UI remain responsive under load.

**Warning signs:**
- First AI action after idle is dramatically slower than the rest.
- CPU spikes correlate with scroll jank or delayed clicks.
- Users stop invoking AI because they “lose flow.”
- Perf fixes focus on prompt tweaks while UI thread remains blocked.

**Phase to address:**
Fast-client UX phase and AI integration phase together.

---

### Pitfall 5: Assuming SQLite concurrency is “free enough” forever

**What goes wrong:**
Search, indexing, daemon sorting, and UI reads start fighting. WAL files grow, occasional commits spike, `SQLITE_BUSY` appears, or worst-case corruption risk rises when concurrency is mishandled.

**Why it happens:**
SQLite is a great fit for app-local storage, so teams stop thinking about read/write patterns. But there is still one writer at a time, WAL checkpoint behavior matters, and long readers can starve checkpoints.

**How to avoid:**
- Keep SQLite local to the app process boundary; never treat the DB file like a shared network database.
- Use WAL intentionally, with busy handling and explicit checkpoint strategy during idle/background windows.
- Separate high-frequency read paths from write-heavy indexing/automation paths with short transactions.
- Monitor WAL size, checkpoint latency, busy errors, and transaction duration.
- Pin SQLite to a version that includes current WAL fixes; upgrade deliberately.

**Warning signs:**
- Search gets slower over the day, then recovers after restart.
- Background indexing causes UI pauses or busy errors.
- WAL file grows without bound.
- Multiple long-lived read transactions stay open while daemon writes continuously.

**Phase to address:**
Local storage hardening phase, before scaling background jobs and advanced search.

---

### Pitfall 6: Modeling “local-first” as local cache instead of source of truth

**What goes wrong:**
Offline behavior is flaky, restores are incomplete, and migrations/backups are fragile. The app feels like a cloud client wearing a local costume.

**Why it happens:**
Projects say “local-first” but still treat server state as authoritative and local state as disposable cache. That undermines responsiveness, explainability, and user trust in their own archive.

**How to avoid:**
- Define which data is canonical locally: metadata index, AI annotations, user triage state, drafts, audit history, rules.
- Make local export/backup/restore a first-class workflow, not a future admin task.
- Store user-created intelligence in portable formats or documented schemas.
- Design startup and degraded modes so the app still works meaningfully without immediate network round-trips.
- Distinguish remote mailbox truth from local product truth: server message exists remotely; user workflow state exists locally.

**Warning signs:**
- Reinstalling loses AI annotations or triage history.
- Backup story is “copy some files, probably.”
- Offline mode can view mail but not continue triage decisions.
- Recovery requires remote re-fetch plus ad hoc scripts.

**Phase to address:**
Foundation / local data architecture phase.

---

### Pitfall 7: Automating before upstream ingest is stable

**What goes wrong:**
Mail gets classified or moved before Paperless and related downstream systems have observed it. The user loses the guarantee that the document pipeline saw the original message at the right time.

**Why it happens:**
Automation is wired directly to “new mail arrived” rather than to a staged lifecycle. Existing brownfield systems already have ingest timing assumptions, but new AI flows bypass them.

**How to avoid:**
- Encode explicit processing states: received → cooling-off delay → Paperless-ingested/eligibility confirmed → AI triage eligible → moved.
- Keep delay logic auditable and per-account configurable, but not silently bypassable.
- Make automation explain why a message is not yet eligible.
- Add invariant tests around the 30-minute delay and max-15-per-run throttle.
- Log upstream/downstream correlation IDs where possible.

**Warning signs:**
- Users ask whether a moved message was seen by Paperless.
- Operators rerun import/sort jobs manually after every daemon cycle.
- Automation bugs are timing-dependent and hard to reproduce.
- A single “new mail” queue feeds both indexing and folder-moving without state gates.

**Phase to address:**
Delayed automation / workflow orchestration phase.

---

### Pitfall 8: Shipping “fast” UX without keyboard-state rigor

**What goes wrong:**
The app looks minimal but feels brittle: focus jumps, shortcuts trigger the wrong pane, optimistic bulk actions misfire, and users cannot maintain triage flow.

**Why it happens:**
Projects copy visual motifs from Superhuman-style clients but not the underlying interaction discipline. Fast mail UX is mostly predictable focus, latency hiding, and reversible actions — not dark mode plus shortcuts.

**How to avoid:**
- Treat keyboard flow, focus management, and command semantics as core product architecture.
- Make every high-frequency action reversible and visually confirmed.
- Keep list state, selection state, thread state, and draft state explicit.
- Add interaction tests for rapid triage sequences, not just component snapshots.
- Measure “time to next meaningful action,” not only render time.

**Warning signs:**
- Users reach for the mouse after every 2–3 actions.
- Shortcut bugs reproduce only during rapid use.
- Bulk triage requires waiting for refreshes before the next action.
- Demo looks smooth; real inbox use feels anxious.

**Phase to address:**
Fast-client UX phase.

---

### Pitfall 9: Treating reply generation as one-shot text generation

**What goes wrong:**
Drafts sound plausible but ignore thread context, miss commitments, or invent facts. Users spend more time fixing tone and accuracy than writing from scratch.

**Why it happens:**
Teams frame replies as prompt-in / answer-out. Real email reply assistance needs thread context, sender relationship, quoted context boundaries, and constrained output shapes.

**How to avoid:**
- Generate replies from a structured context object: current message, selected prior thread messages, account persona, snippets, and user intent.
- Separate draft planning from final phrasing when quality matters.
- Support rewrite operations (shorter, firmer, friendlier, translate) instead of regenerating from scratch.
- Keep citation/context preview so users see what the model actually used.
- Never auto-send from generated content in v1.

**Warning signs:**
- Drafts answer the wrong question in multi-message threads.
- Users repeatedly paste missing context into the prompt box.
- “Looks good” drafts contain invented next steps or dates.
- Success is measured by token count or style, not edit distance to sendable reply.

**Phase to address:**
Reply assistant phase.

---

### Pitfall 10: Neglecting local privacy boundaries because there is no cloud

**What goes wrong:**
Sensitive mail content leaks through logs, prompt traces, desktop notifications, crash dumps, or insecure local files. The app remains “cloud-free” but still violates user expectations and possibly compliance goals.

**Why it happens:**
Teams correctly avoid SaaS dependencies, then relax because everything is on localhost. Local systems still create attack surfaces and accidental disclosure paths.

**How to avoid:**
- Classify local data stores: mailbox index, AI cache, embeddings/RAG store, logs, telemetry, exported backups, secrets.
- Redact or hash message content in logs by default.
- Keep secrets and tokens outside the main app DB where practical.
- Give users explicit controls for retention of prompts, generations, and notification previews.
- Document backup/encryption expectations for a GDPR-sensitive local deployment.

**Warning signs:**
- Full email bodies appear in debug logs.
- Crash reports or Telegram notifications include sensitive content.
- Secrets sit next to ordinary app state with broad file permissions.
- “Private by design” claims rely only on “we do not use cloud APIs.”

**Phase to address:**
Security/privacy hardening phase, before broad user adoption.

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store remote identity as mailbox + sequence number | Faster first implementation | Wrong-message actions after expunge/reorder | Never |
| Trigger summarization/reply generation on message open | Feels “smart” in demos | UI stalls, wasted inference, user distrust | Only in small prototypes |
| Recompute threads entirely on every list render | Simpler code path | Slow inboxes, unstable expansion state | Only before dedicated threading cache exists |
| Use one generic automation confidence score | Easy dashboard metric | Hides dangerous false positives by action type | Never |
| Let daemon and UI share long-lived SQLite transactions | Fewer explicit coordination rules | Busy errors, WAL growth, sporadic slowness | Never |
| Treat local DB as disposable cache | Easy resync story | Lost annotations, weak backup/restore, broken local-first promise | Never |
| Hardcode Trash/Sent/Drafts assumptions | Faster integration | Breaks on provider/account differences | Only if override UI ships immediately |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| IMAP | Using sequence numbers as durable IDs | Use UID + UIDVALIDITY; resync explicitly |
| IMAP | Assuming server responses arrive only when requested | Accept unsolicited updates and keep local state mutable |
| IMAP | Fetching huge ranges or whole messages by default | Batch fetch, partial fetch large bodies, lazy-load detail |
| SMTP / reply flow | Treating generated reply as ready-to-send without review | Keep human review in loop; preserve quoted context and thread metadata |
| Ollama | Calling model generation inline on interaction path | Queue/background AI work, stream results, cache intelligently |
| SQLite | Enabling WAL and forgetting checkpoint strategy | Monitor WAL, keep reads short, checkpoint intentionally |
| Paperless / upstream ingest | Moving mail before upstream ingest window is satisfied | Model explicit eligibility states and delay gates |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full-folder metadata fetch on mailbox open | Long wait entering large inboxes | Batch and lazy-load, fetch viewport-first | Hundreds to thousands of messages |
| Whole-message fetch for attachment indicators | Slow preview on rich mail | Prefer envelope/bodystructure metadata first | Large attachments / mailing-list traffic |
| Long-lived read transactions in SQLite WAL mode | WAL growth, slower reads, busy errors | Short transactions, scheduled checkpoints, metrics | Background indexing + active search/triage |
| Inline local LLM inference for summaries | Scroll/click lag, CPU spikes | Background jobs + cached summaries + streaming UI | Any mid-size inbox on commodity hardware |
| Re-threading everything after each action | Selection jumps, list jank | Incremental thread cache updates | Large threads / unified inboxes |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging raw prompts, message bodies, or generated replies | Sensitive local data disclosure | Redact by default; gated debug logging |
| Mixing secrets and ordinary app state in one casually backed-up store | Credential leakage | Separate secret storage and tighten file permissions |
| Rich notifications with subject/body previews on shared devices | Privacy breach | Configurable notification redaction |
| Treating local RAG/embedding stores as harmless metadata | Hidden retention of sensitive content | Document retention, offer purge/rebuild controls |
| Telegram/admin alerts containing message content | External disclosure path | Send operational metadata only |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| AI actions without reasons | Users do not trust triage | Show confidence + rationale + undo |
| Fast-looking UI with unstable focus | Triage flow breaks under real use | Design keyboard/focus model first |
| Threading tied to sorting mode | Conversation view becomes confusing | Separate thread structure from sibling sort |
| Hidden automation delays | Users think the app is broken | Expose eligibility state and next run time |
| Reply assistant that hides used context | Users over-trust hallucinated drafts | Show context sources and allow quick edits |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **AI triage:** Often missing per-action precision tracking — verify move accuracy separately from tag/priority accuracy.
- [ ] **Thread view:** Often missing broken-header and missing-parent handling — verify against messy real-world mail.
- [ ] **Fast inbox UX:** Often missing focus/selection regression tests — verify rapid keyboard triage sequences.
- [ ] **Local-first storage:** Often missing backup/restore and migration drills — verify a clean reinstall preserves local intelligence.
- [ ] **Delayed automation:** Often missing explicit state machine — verify Paperless delay and run caps are enforced in code, not convention.
- [ ] **Privacy posture:** Often missing log/notification audits — verify sensitive content does not leave the machine unintentionally.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong-message actions from unstable IDs | HIGH | Freeze destructive actions, rebuild mailbox state from UID/UIDVALIDITY, restore from audit log if available |
| Broken or unstable threading | MEDIUM | Recompute thread cache from canonical headers, fall back to flat chronological view temporarily |
| Over-aggressive AI sorting | HIGH | Add global automation pause, expose recent move log, support bulk undo/back-move |
| SQLite contention / WAL growth | MEDIUM | Kill long readers, run checkpoint, trim transaction scope, upgrade SQLite if affected version is old |
| Lost local annotations after reinstall/migration | HIGH | Restore from backup/export, add schema versioning and backup validation before next release |
| Premature Paperless-sensitive moves | MEDIUM | Requeue affected messages into pending state and rerun ingest eligibility workflow |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| IMAP identity drift | Foundation / sync model | Simulated expunge/reconnect tests never target wrong message |
| Broken threading on messy mail | Conversation UX | Corpus tests with malformed/missing headers produce stable trees |
| Unsafe AI automation | AI triage | Undo log, dry-run mode, and per-action precision dashboards exist |
| UI blocked by local LLMs | Fast-client UX + AI integration | Navigation remains responsive while summaries generate |
| SQLite/WAL contention | Storage hardening | WAL size, busy errors, and checkpoint latency stay bounded under load |
| Fake local-first architecture | Local data architecture | Backup/restore drill preserves local state and annotations |
| Paperless race conditions | Delayed automation orchestration | Eligibility state machine enforces delay and gating invariants |
| Keyboard flow brittleness | Fast-client UX | High-frequency triage can be completed mouse-free without focus bugs |
| Weak reply assistant context handling | Reply assistant | Drafts reference the correct thread context and require less manual repair |
| Local privacy leakage | Security/privacy hardening | Logs, notifications, and alerts pass sensitive-content audit |

## Sources

- Project context: `.planning/PROJECT.md` (HIGH for product-specific constraints)
- RFC 9051 — IMAP4rev2, especially UID/UIDVALIDITY, sequence numbers, unsolicited responses, and flags: https://www.rfc-editor.org/rfc/rfc9051 (HIGH)
- RFC 3501 — IMAP4rev1, same core identity/resync semantics: https://www.rfc-editor.org/rfc/rfc3501 (HIGH)
- RFC 2683 — IMAP implementation recommendations on multiple access, flood control, FETCH behavior, and UID pitfalls: https://www.rfc-editor.org/rfc/rfc2683 (HIGH)
- SQLite “Appropriate Uses For SQLite”: https://www.sqlite.org/whentouse.html (HIGH)
- SQLite WAL documentation, including one-writer limits, checkpoints, WAL growth, and 2026 WAL-reset fix notes: https://www.sqlite.org/wal.html (HIGH)
- Ollama API docs and streaming guidance: https://docs.ollama.com/api and https://docs.ollama.com/api/streaming (HIGH)
- Ink & Switch, “Local-first software”: https://www.inkandswitch.com/essay/local-first/ (MEDIUM for principles; not email-specific)
- Jamie Zawinski, “Message Threading”: https://www.jwz.org/doc/threading.html (MEDIUM; old but still foundational and field-tested)

---
*Pitfalls research for: local-first AI mail client / intelligent email sorter*
*Researched: 2026-04-17*
