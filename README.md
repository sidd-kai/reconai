# ReconAI — AI Finance Controller for Multi-Source Reconciliation

ReconAI is a deterministic finance-controller system built for the **Razorpay Buildathon — Track 04: AI Finance Controller (Multi-Source Reconciliation)**.

It reconciles financial records across multiple sources such as Razorpay payments, merchant ledger entries, and settlement evidence using a reliability-first pipeline:

**Exact Match → Fuzzy / Windowed Match → Exception Quarantine**

The AI layer is intentionally separated from financial truth. Deterministic tools compute and verify reconciliation results; the LLM is used only for tool selection, explanation, and finance-operations interaction.

---

## Problem

Finance teams often need to reconcile payment-provider records against internal ledgers and settlement data.

Real reconciliation is difficult because source records may contain:

- missing rows
- amount mismatches
- duplicate evidence
- ambiguous references
- delayed settlement evidence
- malformed records
- source-system ordering differences

A naive matcher can silently link the wrong records and create incorrect financial conclusions.

ReconAI is designed around the opposite principle:

> **When evidence is uncertain, quarantine it instead of silently resolving it.**

---

## Core Goals

ReconAI focuses on five reliability requirements:

1. **Zero silent duplicate matching**
2. **Deterministic multi-tier reconciliation**
3. **Malformed-row quarantine**
4. **Honest exception reporting**
5. **Immutable audit evidence**

The AI agent never mutates financial state and is never treated as the source of truth.

---

## Architecture

```text
                    ┌─────────────────────┐
                    │   Razorpay Test     │
                    │   Mode Payments     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Normalization     │
                    │   + Validation      │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
     Payment Evidence    Merchant Ledger    Settlement Evidence
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ ReconciliationEngine│
                    ├─────────────────────┤
                    │ 1. Exact Match      │
                    │ 2. Fuzzy / Windowed │
                    │ 3. Quarantine       │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼──────────────────┐
             │                 │                  │
             ▼                 ▼                  ▼
       Match Results    Exception Manifest   Immutable Audit
             │                 │                  │
             └─────────────────┼──────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Finance Controller  │
                    │ Agent + Dashboard   │
                    └─────────────────────┘
```

---

## Reconciliation Outcomes

ReconAI currently supports deterministic outcomes including:

- `MATCHED`
- `FUZZY_MATCHED`
- `AMOUNT_MISMATCH`
- `MISSING_PAYMENT`
- `MISSING_LEDGER`
- `DUPLICATE`
- `SETTLEMENT_MISMATCH`
- `AMBIGUOUS`
- `UNRESOLVED`

### Safety rule

A transaction is automatically resolved only when the deterministic engine has sufficient evidence.

If multiple plausible candidates exist, ReconAI emits `AMBIGUOUS` rather than selecting one silently.

---

## Synthetic Benchmark

ReconAI is evaluated using a controlled benchmark with hidden ground truth.

### Dataset

- **1,000 canonical transactions**
- **1,010 raw reconciliation decisions**
- **10 supplemental source events**

### Reconciliation Results

| Metric | Result |
|---|---:|
| Canonical transactions | 1,000 |
| Automatically reconciled | 705 |
| Canonical exceptions | 295 |
| Match rate | **70.50%** |
| Exception rate | **29.50%** |
| Precision | **100%** |
| Recall | **100%** |
| F1 | **100%** |
| Classification accuracy | **100%** |
| Linkage correctness | **100%** |
| Unsafe duplicate resolutions | **0** |
| Integrity | **PASS** |

The benchmark intentionally includes difficult reconciliation scenarios rather than optimizing for a superficially high match rate.

---

## Engine Performance

Measured on the actual deterministic reconciliation engine, including immutable audit writes and exception-manifest writes:

| Metric | Result |
|---|---:|
| Median throughput | **~238.5 canonical records/sec** |
| Mean throughput | ~235 records/sec |
| Median raw decision throughput | ~240.9 decisions/sec |
| Median full-batch latency | ~4.19 sec |

Source loading is excluded from this benchmark.

---

## Razorpay Integration

ReconAI includes two Razorpay Test Mode integration paths.

### 1. REST API Reconciliation Demo

The frontend can fetch current Razorpay Test Mode payments and run them through the real deterministic reconciliation engine.

```text
Razorpay Test Mode REST API
        ↓
Fetch current payments
        ↓
Normalize + adapt
        ↓
Select captured payments
        ↓
Attach controlled merchant evidence
        ↓
ReconciliationEngine
        ↓
MATCHED / EXCEPTION
```

For the working demo:

- Razorpay payment records are **real Test Mode API records**
- merchant ledger evidence is a **controlled fixture**
- settlement evidence is a **controlled synthetic fixture**
- Razorpay payment records themselves are not modified

The demo intentionally injects merchant-side scenarios such as:

- exact match
- amount mismatch
- missing ledger
- ambiguous ledger candidates

This demonstrates how ReconAI responds to realistic reconciliation failures.

---

### 2. Webhook Ingestion

ReconAI also supports event-driven Razorpay ingestion.

```text
Razorpay payment.captured
        ↓
Cloudflare Tunnel / public HTTPS endpoint
        ↓
POST /webhooks/razorpay
        ↓
HMAC verification
        ↓
Idempotency protection
        ↓
Payment normalization
        ↓
Persisted payment evidence
        ↓
Reconciliation
```

The dashboard surfaces persisted webhook evidence separately from REST API demo data.

Verified Test Mode webhook flow:

- `payment.captured` received
- valid webhook signature required
- repeated events deduplicated
- payment evidence persisted
- dashboard counters update from persisted events

---

## Finance Controller Agent

ReconAI includes a finance-controller agent backed by deterministic registered tools.

Examples:

- batch summary
- finance-operations summary
- high-value exception retrieval
- transaction investigation
- exception manifest
- immutable audit-chain verification

### AI safety boundary

The LLM does **not**:

- calculate authoritative reconciliation totals
- mutate transaction state
- approve or settle payments
- silently resolve exceptions
- replace deterministic reconciliation logic

Instead:

```text
User request
    ↓
AI selects approved finance tool
    ↓
Deterministic tool executes
    ↓
Authoritative evidence returned
    ↓
AI may explain the evidence
```

ReconAI uses a provider-neutral LLM abstraction with runtime provider selection.

Current preferred provider:

- **Groq**
- default model: `openai/gpt-oss-20b`

Provider selection is controlled by `LLM_PROVIDER` and available API keys. If `LLM_PROVIDER` is not set, ReconAI prefers Groq when `GROQ_API_KEY` is available and otherwise falls back to Gemini when `GEMINI_API_KEY` is configured.

Provider failure does not disable deterministic finance operations.

---

## Immutable Audit Trail

ReconAI writes reconciliation decisions to an append-only JSON-lines audit trail.

Audit records are hash-linked and can be verified cryptographically.

The frontend exposes a deterministic **Verify Audit Chain** action.

Example verified run:

- audit verification: `true`
- records verified: `4,040`
- financial state mutated: `NO`

---

## Exception Manifest

ReconAI maintains an honest exception manifest for unresolved financial evidence.

The frontend includes an Exception Explorer with:

- search
- status filtering
- pagination
- transaction inspection
- deterministic reason
- source evidence
- amount difference
- confidence
- recommended human action
- audit-history linkage

---

## Frontend

The dashboard is implemented using **Next.js + Tailwind CSS**.

Key sections:

- reconciliation KPI dashboard
- precision / recall / F1
- exception breakdown
- engine performance
- high-value exceptions
- integrity verification
- Razorpay webhook evidence
- Razorpay live reconciliation demo
- exception explorer
- Finance Controller Agent

---

## Tech Stack

### Backend

- Python 3.11+
- FastAPI
- Pydantic v2
- Pandas
- SQLAlchemy
- PostgreSQL-ready persistence architecture

### Frontend

- Next.js
- TypeScript
- Tailwind CSS

### Integration

- Razorpay Test Mode REST APIs
- Razorpay webhook HMAC verification
- Cloudflare Tunnel for local webhook testing
- Groq LLM provider
- Gemini fallback provider through the same provider-neutral contract

---

## Project Structure

```text
reconai/
├── backend/
│   └── app/
│       ├── agent/
│       ├── api/
│       │   └── routes/
│       ├── integrations/
│       │   └── razorpay/
│       ├── reconciliation/
│       ├── services/
│       └── main.py
│
├── data/
│   └── results/
│       ├── audit.jsonl
│       ├── exceptions.jsonl
│       ├── reconciliation_evaluation.json
│       ├── reconciliation_engine_benchmark.json
│       └── razorpay_demo/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
│
├── scripts/
└── README.md
```

---

## Running Locally

### Backend

Set required environment variables.

Example:

```powershell
$env:RAZORPAY_KEY_ID="..."
$env:RAZORPAY_KEY_SECRET="..."
$env:RAZORPAY_WEBHOOK_SECRET="..."
$env:GROQ_API_KEY="..."
$env:LLM_PROVIDER="groq"
```

Optional Groq configuration:

```powershell
$env:GROQ_MODEL="openai/gpt-oss-20b"
$env:GROQ_TIMEOUT_SECONDS="45"
$env:GROQ_MAX_RETRIES="3"
$env:GROQ_BACKOFF_SECONDS="1"
$env:GROQ_MAX_CONCURRENCY="2"
$env:GROQ_MAX_OUTPUT_TOKENS="1024"
```

`LLM_PROVIDER` is optional. When omitted, ReconAI selects Groq if `GROQ_API_KEY` is configured; otherwise it can fall back to Gemini if `GEMINI_API_KEY` is available.

Start FastAPI:

```powershell
cd E:\GIT\reconai

python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001
```

Health check:

```text
http://127.0.0.1:8001/health
```

API documentation:

```text
http://127.0.0.1:8001/docs
```

---

### Frontend

Create:

```text
frontend/.env.local
```

with:

```env
RECONAI_API_URL=http://127.0.0.1:8001
```

Run:

```powershell
cd E:\GIT\reconai\frontend

npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## Production Build Check

```powershell
cd E:\GIT\reconai\frontend

npx tsc --noEmit
npm run build
```

Current status:

- TypeScript validation: **PASS**
- Next.js production compilation: **PASS**
- dynamic dashboard rendering: **PASS**

---

## Testing Razorpay Webhooks Locally

Run FastAPI on port `8001`.

Then expose it using Cloudflare Tunnel:

```powershell
cloudflared tunnel --url http://localhost:8001
```

Cloudflare will provide a temporary public HTTPS endpoint.

Configure the Razorpay Test Mode webhook as:

```text
https://<generated-domain>.trycloudflare.com/webhooks/razorpay
```

Recommended demo events:

```text
payment.captured
payment.failed
```

The webhook secret configured in Razorpay must match:

```text
RAZORPAY_WEBHOOK_SECRET
```

After creating a new Test Mode payment, a successful delivery should return HTTP `200`.

---

## Reliability Design

ReconAI follows several non-negotiable safety rules.

### No silent duplicate resolution

Competing evidence is never silently resolved.

### Exception-first uncertainty handling

Uncertain transactions are routed to the exception manifest.

### Deterministic financial truth

LLM output is not used as authoritative reconciliation data.

### Immutable audit evidence

Every reconciliation result is recorded for inspection and verification.

### Malformed-row quarantine

Bad source records do not silently enter the reconciliation path.

---

## Known Limitations

ReconAI is a Buildathon prototype and intentionally documents its current limits.

- Razorpay settlement evidence in the live demo uses a controlled synthetic fixture because current Test Mode settlement data was unavailable.
- Local JSONL persistence is not transactionally atomic across multiple files.
- Production webhook idempotency should use PostgreSQL transactions with a unique event identifier.
- Cloudflare Quick Tunnel URLs are temporary and change when the tunnel is restarted.
- AI provider availability can vary; deterministic finance tools remain operational independently.
- Groq is the preferred provider in the current demo configuration, while Gemini remains supported as a fallback through the provider factory.

---

## Demo Story

A recommended judge flow:

1. Show benchmark metrics.
2. Explain why 70.50% automatic match rate is safer than forcing uncertain matches.
3. Filter and inspect an `AMBIGUOUS` exception.
4. Verify the immutable audit chain.
5. Run a Finance Controller quick action.
6. Trigger a real Razorpay Test Mode payment webhook.
7. Refresh the dashboard and show persisted webhook evidence.
8. Run the Razorpay reconciliation demo.
9. Inspect `MATCHED`, `AMOUNT_MISMATCH`, `MISSING_LEDGER`, and `AMBIGUOUS`.
10. Close with:
   - 100% precision / recall / F1
   - 0 unsafe duplicate resolutions
   - deterministic financial truth
   - AI only as an explanation and orchestration layer

---

## Why ReconAI

ReconAI is designed around a simple finance principle:

> **A system that admits uncertainty is safer than one that silently invents certainty.**

The goal is not to maximize automatic matching at any cost.

The goal is to automatically reconcile what can be proven, quarantine what cannot, and leave an auditable trail explaining every decision.

---

## Buildathon

**Project:** ReconAI  
**Track:** Track 04 — AI Finance Controller  
**Platform Integration:** Razorpay Test Mode  
**AI Provider:** Groq (`openai/gpt-oss-20b`) with Gemini fallback support  
**Frontend:** Next.js  
**Backend:** FastAPI  
