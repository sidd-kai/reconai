"use client";

import {
    CheckCircle2,
    FileCheck2,
    Fingerprint,
    Link2,
    Loader2,
    LockKeyhole,
    RefreshCw,
    ShieldAlert,
    ShieldCheck,
    XCircle,
} from "lucide-react";

import {
    useState,
} from "react";

import type {
    AuditStatus,
    AuditVerificationResponse,
    DashboardSummary,
} from "@/lib/types";


interface IntegrityPanelProps {
    summary: DashboardSummary;
    audit: AuditStatus;
}


function formatEvidenceValue(
    value: unknown,
): string {
    if (
        value === null ||
        value === undefined
    ) {
        return "—";
    }

    if (
        typeof value ===
        "string" ||
        typeof value ===
        "number" ||
        typeof value ===
        "boolean"
    ) {
        return String(
            value,
        );
    }

    return JSON.stringify(
        value,
    );
}


export function IntegrityPanel({
    summary,
    audit,
}: IntegrityPanelProps) {
    const [
        verification,
        setVerification,
    ] = useState<
        AuditVerificationResponse | null
    >(
        null,
    );

    const [
        verifying,
        setVerifying,
    ] = useState(
        false,
    );

    const [
        verificationError,
        setVerificationError,
    ] = useState<
        string | null
    >(
        null,
    );


    const checks = [
        {
            label:
                "Benchmark integrity",

            passed:
                summary.integrity_passed,

            icon:
                ShieldCheck,

            detail:
                "Synthetic benchmark integrity gate",
        },
        {
            label:
                "Unsafe duplicate resolutions",

            passed:
                summary.unsafe_duplicate_resolutions ===
                0,

            icon:
                CheckCircle2,

            detail:
                `${summary.unsafe_duplicate_resolutions} unsafe resolutions`,
        },
        {
            label:
                "Linkage correctness",

            passed:
                summary.linkage_f1 ===
                1,

            icon:
                Link2,

            detail:
                `${(
                    summary.linkage_f1 *
                    100
                ).toFixed(
                    2,
                )}% linkage F1`,
        },
        {
            label:
                "Immutable audit evidence",

            passed:
                audit.audit_file_exists &&
                audit.audit_record_count >
                0,

            icon:
                FileCheck2,

            detail:
                `${audit.audit_record_count.toLocaleString()} audit records`,
        },
    ];


    async function verifyAudit(): Promise<void> {
        setVerifying(
            true,
        );

        setVerificationError(
            null,
        );

        setVerification(
            null,
        );

        try {
            const response =
                await fetch(
                    "/api/reconai/audit/verify",
                    {
                        method: "POST",
                        cache: "no-store",
                    },
                );

            const contentType =
                response.headers.get(
                    "content-type",
                ) ?? "";

            const rawBody =
                await response.text();

            if (
                !contentType.includes(
                    "application/json",
                )
            ) {
                throw new Error(
                    `Audit verification returned non-JSON (${response.status}).`,
                );
            }

            const payload =
                JSON.parse(
                    rawBody,
                ) as
                | AuditVerificationResponse
                | {
                    detail?: string;
                };

            if (
                !response.ok
            ) {
                throw new Error(
                    "detail" in payload &&
                        typeof payload.detail ===
                        "string"
                        ? payload.detail
                        : "Audit verification failed.",
                );
            }

            setVerification(
                payload as AuditVerificationResponse,
            );
        } catch (
        caught
        ) {
            console.error(
                "[ReconAI] Audit verification failed:",
                caught,
            );

            setVerificationError(
                caught instanceof Error
                    ? caught.message
                    : "Audit verification failed.",
            );
        } finally {
            setVerifying(
                false,
            );
        }
    }


    return (
        <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-6">
            {/* -------------------------------------------------- */}
            {/* HEADER */}
            {/* -------------------------------------------------- */}

            <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                    <h2 className="text-base font-semibold text-white">
                        System Integrity
                    </h2>

                    <p className="mt-1 text-sm text-zinc-500">
                        Deterministic safety and immutable evidence checks.
                    </p>
                </div>

                <div className="rounded-xl border border-emerald-500/15 bg-emerald-500/[0.06] p-2">
                    <Fingerprint className="h-4 w-4 text-emerald-400" />
                </div>
            </div>

            {/* -------------------------------------------------- */}
            {/* STATIC INTEGRITY CHECKS */}
            {/* -------------------------------------------------- */}

            <div className="space-y-3">
                {checks.map(
                    ({
                        label,
                        passed,
                        icon: Icon,
                        detail,
                    }) => (
                        <div
                            key={label}
                            className="flex items-center justify-between rounded-xl border border-white/[0.07] bg-black/20 p-4"
                        >
                            <div className="flex items-center gap-3">
                                <div
                                    className={`rounded-lg p-2 ${passed
                                            ? "bg-emerald-500/10"
                                            : "bg-rose-500/10"
                                        }`}
                                >
                                    <Icon
                                        className={`h-4 w-4 ${passed
                                                ? "text-emerald-400"
                                                : "text-rose-400"
                                            }`}
                                    />
                                </div>

                                <div>
                                    <p className="text-sm font-medium text-zinc-200">
                                        {label}
                                    </p>

                                    <p className="mt-0.5 text-xs text-zinc-600">
                                        {detail}
                                    </p>
                                </div>
                            </div>

                            <span
                                className={`text-xs font-medium ${passed
                                        ? "text-emerald-400"
                                        : "text-rose-400"
                                    }`}
                            >
                                {passed
                                    ? "PASS"
                                    : "FAIL"}
                            </span>
                        </div>
                    ),
                )}
            </div>

            {/* -------------------------------------------------- */}
            {/* CRYPTOGRAPHIC VERIFICATION */}
            {/* -------------------------------------------------- */}

            <div className="mt-5 overflow-hidden rounded-xl border border-indigo-500/15 bg-indigo-500/[0.04]">
                <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-start gap-3">
                        <div className="rounded-lg border border-indigo-500/15 bg-indigo-500/10 p-2">
                            <LockKeyhole className="h-4 w-4 text-indigo-300" />
                        </div>

                        <div>
                            <p className="text-sm font-medium text-zinc-200">
                                Cryptographic Audit Chain
                            </p>

                            <p className="mt-1 max-w-sm text-xs leading-5 text-zinc-600">
                                Recompute and verify the immutable hash chain using
                                ReconAI&apos;s canonical verification tool.
                            </p>
                        </div>
                    </div>

                    <button
                        type="button"
                        disabled={
                            verifying
                        }
                        onClick={() => {
                            void verifyAudit();
                        }}
                        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-indigo-500/20 bg-indigo-500/10 px-4 py-2.5 text-xs font-medium text-indigo-300 transition hover:border-indigo-500/40 hover:bg-indigo-500/15 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {verifying ? (
                            <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />

                                Verifying...
                            </>
                        ) : verification ? (
                            <>
                                <RefreshCw className="h-3.5 w-3.5" />

                                Verify Again
                            </>
                        ) : (
                            <>
                                <ShieldCheck className="h-3.5 w-3.5" />

                                Verify Audit Chain
                            </>
                        )}
                    </button>
                </div>

                {/* ------------------------------------------------ */}
                {/* VERIFICATION SUCCESS/FAIL */}
                {/* ------------------------------------------------ */}

                {verification && (
                    <div
                        className={`border-t p-4 ${verification.verified
                                ? "border-emerald-500/10 bg-emerald-500/[0.04]"
                                : "border-rose-500/10 bg-rose-500/[0.04]"
                            }`}
                    >
                        <div className="flex items-start gap-3">
                            {verification.verified ? (
                                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
                            ) : (
                                <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
                            )}

                            <div className="min-w-0 flex-1">
                                <p
                                    className={`text-sm font-semibold ${verification.verified
                                            ? "text-emerald-300"
                                            : "text-rose-300"
                                        }`}
                                >
                                    {verification.verified
                                        ? "Audit chain verified"
                                        : "Audit chain verification failed"}
                                </p>

                                <div className="mt-3 space-y-2">
                                    <div className="flex items-center justify-between gap-4">
                                        <span className="text-xs text-zinc-600">
                                            Deterministic tool
                                        </span>

                                        <span className="font-mono text-xs text-zinc-300">
                                            {verification.tool_name}
                                        </span>
                                    </div>

                                    <div className="flex items-center justify-between gap-4">
                                        <span className="text-xs text-zinc-600">
                                            Financial state mutated
                                        </span>

                                        <span
                                            className={`text-xs font-medium ${verification.financial_state_mutated
                                                    ? "text-rose-400"
                                                    : "text-emerald-400"
                                                }`}
                                        >
                                            {verification.financial_state_mutated
                                                ? "YES"
                                                : "NO"}
                                        </span>
                                    </div>
                                </div>

                                {verification.evidence &&
                                    Object.keys(
                                        verification.evidence,
                                    ).length >
                                    0 && (
                                        <details className="mt-4">
                                            <summary className="cursor-pointer text-xs font-medium text-zinc-500 transition hover:text-zinc-300">
                                                View verification evidence
                                            </summary>

                                            <div className="mt-3 divide-y divide-white/[0.06] overflow-hidden rounded-lg border border-white/[0.07] bg-black/20">
                                                {Object.entries(
                                                    verification.evidence,
                                                ).map(
                                                    ([
                                                        key,
                                                        value,
                                                    ]) => (
                                                        <div
                                                            key={key}
                                                            className="grid gap-2 px-3 py-2.5 sm:grid-cols-[150px_1fr]"
                                                        >
                                                            <span className="text-xs text-zinc-600">
                                                                {key}
                                                            </span>

                                                            <span className="break-all font-mono text-xs text-zinc-300">
                                                                {formatEvidenceValue(
                                                                    value,
                                                                )}
                                                            </span>
                                                        </div>
                                                    ),
                                                )}
                                            </div>
                                        </details>
                                    )}
                            </div>
                        </div>
                    </div>
                )}

                {/* ------------------------------------------------ */}
                {/* VERIFICATION ERROR */}
                {/* ------------------------------------------------ */}

                {verificationError && (
                    <div className="border-t border-rose-500/10 bg-rose-500/[0.04] p-4">
                        <div className="flex gap-3">
                            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />

                            <div>
                                <p className="text-sm font-medium text-rose-300">
                                    Verification request failed
                                </p>

                                <p className="mt-1 text-xs leading-5 text-rose-300/70">
                                    {verificationError}
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <p className="mt-4 text-xs leading-5 text-zinc-700">
                File presence is not treated as cryptographic verification.
                Chain integrity is reported only after the registered
                verification tool executes.
            </p>
        </section>
    );
}