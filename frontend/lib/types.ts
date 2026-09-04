/*
|--------------------------------------------------------------------------
| Dashboard Summary
|--------------------------------------------------------------------------
*/

export interface DashboardSummary {
    canonical_transactions: number;

    raw_decisions: number;

    supplemental_events: number;

    resolved: number;

    exceptions: number;

    match_rate: number;

    exception_rate: number;

    classification_accuracy: number;

    precision: number;

    recall: number;

    f1: number;

    linkage_precision: number;

    linkage_recall: number;

    linkage_f1: number;

    unsafe_duplicate_resolutions: number;

    integrity_passed: boolean;
}


/*
|--------------------------------------------------------------------------
| Benchmark
|--------------------------------------------------------------------------
*/

export interface BenchmarkData {
    median_records_per_second: number;

    mean_records_per_second: number;

    median_decisions_per_second: number;

    mean_decisions_per_second: number;

    median_latency_seconds: number;

    mean_latency_seconds: number;

    fastest_latency_seconds: number;

    slowest_latency_seconds: number;

    payment_rows: number;

    ledger_rows: number;

    settlement_rows: number;

    deterministic_across_runs: boolean;

    runs?: number;

    [key: string]: unknown;
}


/*
|--------------------------------------------------------------------------
| Exception Evidence
|--------------------------------------------------------------------------
*/

export interface ExceptionEvidence {
    payment_id: string | null;

    ledger_id: string | null;

    settlement_id: string | null;

    amount_difference: number;

    candidate_count: number;

    [key: string]: unknown;
}


/*
|--------------------------------------------------------------------------
| Exceptions
|--------------------------------------------------------------------------
*/

export interface ExceptionItem {
    transaction_id: string;

    status: string;

    reason: string;

    method: string;

    confidence: number;

    amount_difference: number;

    evidence: ExceptionEvidence;

    [key: string]: unknown;
}


export interface ExceptionResponse {
    items: ExceptionItem[];

    total: number;

    status_counts: Record<
        string,
        number
    >;
}


export interface HighValueExceptionResponse {
    items: ExceptionItem[];

    total?: number;

    limit?: number;
}


/*
|--------------------------------------------------------------------------
| Exception Detail
|--------------------------------------------------------------------------
*/

export interface ExceptionDetail {
    transaction_id: string;

    status: string;

    reason: string;

    method: string;

    confidence: number;

    amount_difference: number;

    evidence: ExceptionEvidence;

    recommended_action: string;

    exception_history_count: number;

    audit_record_count: number;

    exception_history: unknown[];

    audit_history: unknown[];

    [key: string]: unknown;
}


/*
|--------------------------------------------------------------------------
| Finance Controller Agent
|--------------------------------------------------------------------------
*/

export type FinanceAgentAction =
    | "batch_summary"
    | "finance_ops_summary"
    | "high_value_exceptions"
    | "verify_audit_chain"
    | "exception_manifest"
    | "investigate_exception";


export interface AgentQueryResponse {
    success: boolean;

    answer: string;

    transaction_id:
    | string
    | null;

    tools_used: string[];

    deterministic_evidence: unknown;

    ai_explanation_used: boolean;

    provider_status: string;

    financial_state_mutated: boolean;
}


/*
|--------------------------------------------------------------------------
| Audit
|--------------------------------------------------------------------------
*/

export interface AuditStatus {
    audit_file_exists: boolean;

    audit_record_count: number;

    [key: string]: unknown;
}


export interface AuditVerificationEvidence {
    verified: boolean;

    records_verified: number;

    error:
    | string
    | null;

    [key: string]: unknown;
}


export interface AuditVerificationResponse {
    success: boolean;

    tool_name: string;

    verified: boolean;

    records_verified: number;

    error:
    | string
    | null;

    financial_state_mutated: boolean;

    evidence:
    | AuditVerificationEvidence
    | Record<string, unknown>
    | null;
}


/*
|--------------------------------------------------------------------------
| Razorpay Existing Dashboard Status
|--------------------------------------------------------------------------
*/

export interface RazorpayPaymentEvidence {
    event_id:
    | string
    | null;

    transaction_id:
    | string
    | null;

    payment_id:
    | string
    | null;

    order_id?:
    | string
    | null;

    status:
    | string
    | null;

    amount?: number;

    currency?: string;

    [key: string]: unknown;
}


export interface RazorpayStatus {
    mode: string;

    webhook_event_count: number;

    payment_evidence_count: number;

    payments: RazorpayPaymentEvidence[];

    [key: string]: unknown;
}


/*
|--------------------------------------------------------------------------
| Razorpay Working Demo
|--------------------------------------------------------------------------
*/

export interface RazorpayDemoSources {
    payment_source: string;

    ledger_source: string;

    settlement_source: string;
}


export interface RazorpayDemoSummary {
    razorpay_payments_ingested: number;

    captured_eligible: number;

    excluded_payment_attempts: number;

    demo_transactions: number;

    automatically_resolved: number;

    canonical_exceptions: number;

    supplemental_source_events: number;

    unsafe_duplicate_resolutions: number;

    passed: boolean;
}


export interface RazorpayDemoTransaction {
    transaction_id: string;

    payment_id: string;

    order_id:
    | string
    | null;

    payment_amount: number;

    currency: string;

    payment_status: string;

    expected_status: string;

    actual_status: string;

    method: string;

    confidence: number;

    ledger_id:
    | string
    | null;

    settlement_id:
    | string
    | null;

    amount_difference: number;

    reason: string;
}


export interface RazorpayDemoSupplementalResult {
    transaction_id: string;

    status: string;

    method: string;

    payment_id:
    | string
    | null;

    ledger_id:
    | string
    | null;

    settlement_id:
    | string
    | null;

    confidence: number;

    amount_difference: number;

    reason: string;
}


export interface RazorpayDemoExcludedPayment {
    payment_id: string;

    transaction_id: string;

    order_id:
    | string
    | null;

    status: string;

    amount: number;

    currency: string;
}


export interface RazorpayDemoResult {
    success: boolean;

    mode: string;

    sources: RazorpayDemoSources;

    summary: RazorpayDemoSummary;

    transactions: RazorpayDemoTransaction[];

    supplemental_results:
    RazorpayDemoSupplementalResult[];

    excluded_payment_attempts:
    RazorpayDemoExcludedPayment[];

    quarantined_payment_count: number;

    audit_artifact: string;

    exception_artifact: string;

    financial_state_mutated: boolean;
}


/*
|--------------------------------------------------------------------------
| Dashboard
|--------------------------------------------------------------------------
*/

export interface DashboardData {
    summary: DashboardSummary;

    benchmark: BenchmarkData;

    exceptions: ExceptionResponse;

    highValueExceptions:
    HighValueExceptionResponse;

    audit: AuditStatus;

    razorpay: RazorpayStatus;
}