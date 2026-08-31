# ReconAI — AI Finance Controller

Razorpay Buildathon — Track 04: AI Finance Controller
Example direction: Multi-source reconciliation

## Goal
Build an agent that closes one finance-ops loop across a 50+ record batch of synthetic financial data, reports match rate and throughput, and surfaces unresolved exceptions.

## Core loop
Payments + Merchant Ledger + Settlements
→ Normalize → Candidate Match → Validate → Reconcile/Exception → Explain → Audit → Report

## Architecture
- Agent orchestrator: plans and executes reconciliation workflow using tools.
- Deterministic rules: finance-safe validation and reconciliation logic.
- ML matcher: scores ambiguous candidate pairs.
- LLM explanation layer: explains decisions; never acts as the source of financial truth.
- PostgreSQL: source of application state.
- Next.js: dashboard.

## Development stages
1. Synthetic data + ground truth
2. Deterministic reconciliation baseline
3. Agent orchestration + tool calls
4. ML-assisted matching
5. Evaluation benchmark
6. Razorpay Test Mode integration
7. Dashboard + human review
8. Hardening + demo
# reconai
# reconai
