# Finance Controller Agent

The agent's job is to close a reconciliation run.

Planned tool contract:
- inspect_batch()
- load_source(name)
- normalize_sources()
- generate_candidates()
- score_candidates()
- validate_financial_consistency()
- reconcile_record()
- create_exception()
- request_human_review()
- write_audit_log()
- generate_report()
