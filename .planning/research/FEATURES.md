# Feature Research

**Domain:** local-first AI-assisted mail client / intelligent email sorter
**Researched:** 2026-04-17
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Fast multi-account inbox with unified view | Thunderbird, Spark, and Canary all treat multi-account management as foundational. | MEDIUM | Already partly present; needs to feel instant and trustworthy for daily use. |
| Thread-first reading and reply UX | Modern clients optimize around grouped conversations, collapse/expand, mute, and follow-up handling. | MEDIUM | Important because the active milestone explicitly targets thread readability and reply flow. |
| Powerful search across mail history | Spark, Shortwave, and Canary all market natural-language or smart search as core. | HIGH | “Search” is no longer just by sender/subject; users expect fast recall across bodies, attachments, and accounts. |
| Keyboard-first triage workflow | Superhuman and Shortwave position speed via shortcuts/command palettes as a core productivity promise. | MEDIUM | Required if the app wants a Superhuman-like feel rather than a basic admin UI. |
| Core triage actions: archive, delete, mark done, star/pin, snooze, mute, labels/tags | These are standard across Spark, Superhuman, Shortwave, and Canary. | MEDIUM | Must be low-friction and available in list view, detail view, and bulk actions. |
| Send later and follow-up reminders | Spark and Superhuman explicitly treat this as standard productivity tooling. | MEDIUM | Important for “don’t drop the ball” workflows even without full automation. |
| Smart inbox prioritization / low-noise filtering | Spark Smart Inbox, Shortwave splits/bundles, Superhuman auto labels, and Canary smart inbox all do this. | HIGH | For this project, combine deterministic rules + AI suggestions rather than opaque automation. |
| Reply assistance inside compose | AI draft/rewrite/summarize is now table stakes among AI-positioned clients. | MEDIUM | Already partially built; target is finishing replies faster, not “chatbot for everything.” |
| Attachment-aware context | Spark AI Assistant and Shortwave both analyze attachments; users increasingly expect this. | HIGH | Especially valuable for invoices, PDFs, and Paperless-adjacent workflows. |
| Privacy and account compatibility messaging | Thunderbird, Spark, and Canary all foreground security/privacy and broad provider support. | MEDIUM | For a local-first product, this is part of the product feature set, not just marketing copy. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Local-first AI with local LLM fallback/default | Most AI mail products still depend on cloud inference even when they use local indexing. True local AI is rare and aligned with the project’s core value. | HIGH | Strongest differentiator if quality is good enough for summary, triage, and draft assistance. |
| Delayed automation pipeline tied to Paperless ingestion | This is unusual in mainstream clients and fits a real document-processing workflow instead of instant-but-brittle automation. | HIGH | Make delay windows, per-account caps, and reviewability first-class. |
| Human-in-the-loop AI triage queue | Better than “full auto” for trust: suggest folder, tag, priority, or reply draft, then let user approve quickly. | MEDIUM | Safer than autonomous agents and matches local/privacy-conscious users. |
| AI-assisted thread compression into action items + next reply | Superhuman/Shortwave summarize threads, but a local client that turns a thread into “what matters / what to send next” is more directly useful. | MEDIUM | Especially valuable for long back-and-forth client/vendor threads. |
| Search that blends lexical filters, semantic recall, and answer mode over local mail | Shortwave and Spark push AI search, but a local index with explicit provenance and no cloud dependence is differentiated. | HIGH | Show linked source emails/snippets to preserve trust. |
| Inbox-as-work-queue for triage sessions | Shortwave’s “method” shows the value of explicit triage states; adapting that to a local power-user client can differentiate the workflow. | MEDIUM | Examples: Needs reply, Waiting, Review after Paperless, Ready to sort. |
| Per-account throttled automation with audit trail | Mainstream tools emphasize power, not restraint. Controlled automation is a differentiator for cautious users. | MEDIUM | Your existing “max 15 emails/account/run” constraint should become visible product behavior, not hidden internals. |
| Reusable reply building blocks + AI personalization | Better than generic AI reply buttons: combine snippets/templates with AI rewrite in the user’s style. | MEDIUM | Strong fit for the project’s 80–90% reply completion goal. |
| Local privacy posture as a product feature | Thunderbird owns privacy, but not AI-native mail assistance; cloud AI clients own AI, but not local privacy. Combining both is distinctive. | LOW | Differentiator only if communicated clearly and backed by architecture. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Fully autonomous send/reply agent by default | Feels futuristic and promises huge time savings. | High trust risk, hallucination risk, tone mistakes, and privacy concerns; dangerous for a local personal mail client. | Keep AI in draft mode by default, with explicit approve/send. |
| “One-click inbox zero” with opaque AI decisions | Attractive because it removes perceived work. | Users lose trust quickly when important messages are archived/labeled incorrectly and cannot understand why. | Use explainable suggestions, reversible bulk actions, and confidence-based review queues. |
| Broad team collaboration for v1 | Many mail tools upsell shared inboxes, comments, assignments. | Out of scope for this single-user/local-first product and likely to distort architecture and UX. | Keep single-user triage first; design extensible metadata later if needed. |
| Mobile app parity in v1 | Users often ask for everywhere access. | Major surface-area explosion; weakens focus on the desktop/web power-user workflow. | Make desktop/web excellent first; mobile can follow after workflow validation. |
| Heavy CRM/project-suite integration layer | Seems useful for “power users.” | Integration sprawl competes with core mail UX and creates maintenance burden. | Support exportable metadata/hooks later; keep v1 focused on email, search, and reply workflows. |
| Aggressive real-time processing of every incoming email | Promises immediacy. | Conflicts with Paperless-first delayed processing and increases noisy automation behavior. | Use scheduled/delayed background runs with clear cadence and caps. |

## Feature Dependencies

```
Local mail sync + indexing
    ├──requires──> Unified inbox
    ├──requires──> Thread view
    └──requires──> Search

Search
    └──requires──> Local index quality + attachment extraction

AI summaries / answer mode
    ├──requires──> Search
    ├──requires──> Thread view
    └──requires──> Local/LLM inference pipeline

Reply generation
    ├──requires──> Compose UX
    ├──requires──> Thread context
    └──enhances──> Snippets/templates

Human-in-the-loop triage
    ├──requires──> Smart inbox prioritization
    ├──requires──> Bulk actions
    └──requires──> Audit/history view

Delayed automation
    ├──requires──> Rules/prompts
    ├──requires──> Background jobs
    ├──requires──> Review/audit trail
    └──conflicts──> Instant opaque full-auto processing
```

### Dependency Notes

- **Search requires local index quality + attachment extraction:** AI search is only credible if the underlying retrieval is fast, complete, and citation-friendly.
- **AI summaries / answer mode require search and thread view:** good summaries depend on clean thread grouping and relevant retrieval, not just an LLM call.
- **Reply generation requires compose UX and thread context:** draft quality is much less useful if users cannot review, edit, and send quickly in-context.
- **Human-in-the-loop triage requires audit/history:** once AI suggests labels, folders, or replies, users need to inspect and undo decisions.
- **Delayed automation conflicts with instant opaque full-auto processing:** the project’s Paperless-first workflow depends on intentional latency and controlled execution.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Fast unified inbox + thread-centric reading — core daily-driver behavior must already beat “just use Gmail/Thunderbird.”
- [ ] Powerful local search with thread and attachment recall — essential for rediscovery and AI assist quality.
- [ ] Keyboard-first triage actions (archive, snooze, tag, bulk, navigate) — required for the “fast minimalist client” promise.
- [ ] AI thread summary + reply draft assistance — the minimum AI value that directly reduces email handling time.
- [ ] Delayed/background sorting with reviewability and per-account caps — core workflow differentiator tied to the project constraints.

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] AI-assisted inbox work queue states (Needs reply / Waiting / Review later) — add when basic triage flow is stable.
- [ ] Snippets/templates with AI personalization — add once reply drafting is reliable and users want more consistency.
- [ ] Answer-mode search over emails + attachments with citations — add when retrieval quality is proven strong.
- [ ] Suggested follow-up reminders / send later timing — add after users trust the system’s prioritization.

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Fully local semantic search and reranking at larger scale — worthwhile, but only after basic indexing/performance is proven.
- [ ] Team/shared inbox features — only if the product expands beyond the current single-user/local-first scope.
- [ ] Mobile clients and cross-device sync — high demand eventually, but not necessary to validate the desktop workflow.
- [ ] More autonomous multi-step agents — only after trust, auditability, and failure handling are mature.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Unified inbox + fast thread view | HIGH | MEDIUM | P1 |
| Local search incl. attachments | HIGH | HIGH | P1 |
| Keyboard-first triage workflow | HIGH | MEDIUM | P1 |
| AI summaries + reply drafts | HIGH | MEDIUM | P1 |
| Delayed reviewed automation | HIGH | HIGH | P1 |
| Snippets/templates + AI rewrite | HIGH | MEDIUM | P2 |
| Work-queue triage states | MEDIUM | MEDIUM | P2 |
| Answer-mode AI search with citations | HIGH | HIGH | P2 |
| Suggested follow-up/send-later timing | MEDIUM | MEDIUM | P2 |
| Team/shared inbox collaboration | LOW | HIGH | P3 |
| Mobile parity | MEDIUM | HIGH | P3 |
| Autonomous reply agent | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Inbox triage speed | **Superhuman:** shortcuts, snooze, send later, instant reply, auto labels | **Shortwave:** bundles, splits, todos, done workflow | Emphasize keyboard speed plus explicit triage states and safer AI suggestions. |
| AI search and answers | **Shortwave:** plain-language AI search + answer mode over history | **Spark:** ask questions across email, attachments, calendar, notes | Build local-first answer mode with citations and stronger privacy guarantees. |
| AI writing | **Canary:** AI Copilot drafts + tone control | **Superhuman:** reply in your voice, follow-up drafting | Focus on reply completion for high-volume mail using local models + snippets/templates. |
| Smart inbox organization | **Spark:** smart inbox categories | **Superhuman/Shortwave:** auto labels, AI filters, bundles | Prefer explainable suggestions and controlled automation over opaque auto-magic. |
| Privacy posture | **Thunderbird:** privacy/open source, no AI-first workflow | **Canary:** claims local AI / zero-access AI | Win by combining local privacy posture with genuinely useful AI-assisted triage. |
| Delayed automation | **Shortwave:** delivery schedules + Tasklet automation | **Others:** mostly immediate categorization/reminders | Make Paperless-delayed reviewable automation a signature workflow. |

## Sources

- Project context: `/Users/michaelkatschko/mail-ai-sorter/.planning/PROJECT.md`
- Superhuman Mail product pages (official, Apr 2026): https://superhuman.com/products/mail , https://superhuman.com/products/mail/ai , https://superhuman.com/products/mail/calendar
- Shortwave official site/docs (official, 2026): https://www.shortwave.com/ , https://www.shortwave.com/pricing/ , https://www.shortwave.com/docs/guides/method/ , https://www.shortwave.com/docs/guides/ai-assistant/
- Spark official features pages (official, 2026): https://sparkmailapp.com/features , https://sparkmailapp.com/features/ai-assistant , https://sparkmailapp.com/features/smart_inbox
- Canary Mail official site/features (official, last updated Mar 20 2026 on features page): https://canarymail.io/ , https://canarymail.io/features
- Thunderbird official product pages (official, 2026): https://www.thunderbird.net/en-US/ , https://www.thunderbird.net/en-US/desktop

---
*Feature research for: local-first AI-assisted mail client / intelligent email sorter*
*Researched: 2026-04-17*
