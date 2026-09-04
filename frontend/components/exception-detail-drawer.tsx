"use client";

import {
    AlertCircle,
    AlertTriangle,
    ArrowRight,
    Bot,
    CheckCircle2,
    Database,
    FileClock,
    Loader2,
    Search,
    Send,
    ShieldCheck,
    Sparkles,
    Wrench,
    X,
} from "lucide-react";

import {
    useState,
} from "react";

import type {
    AgentQueryResponse,
    ExceptionDetail,
} from "@/lib/types";


interface ExceptionDetailDrawerProps {
    open: boolean;
    loading: boolean;

    detail: ExceptionDetail | null;

    error: string | null;

    onClose: () => void;
}


const DEFAULT_AGENT_MESSAGE =
    "Explain why this exception happened and what finance operations should review next.";


function formatMoney(
    value: number,
): string {
    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            maximumFractionDigits: 2,
        },
    ).format(
        Math.abs(
            value,
        ),
    );
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


function providerLabel(
    response: AgentQueryResponse,
): string {
    if (
        response.ai_explanation_used
    ) {
        return "AI explanation";
    }

    return "Deterministic fallback";
}


export function ExceptionDetailDrawer({
    open,
    loading,
    detail,
    error,
    onClose,
}: ExceptionDetailDrawerProps) {
    const [
        agentMessage,
        setAgentMessage,
    ] = useState(
        DEFAULT_AGENT_MESSAGE,
    );

    const [
        agentResponse,
        setAgentResponse,
    ] = useState<
        AgentQueryResponse | null
    >(
        null,
    );

    const [
        agentLoading,
        setAgentLoading,
    ] = useState(
        false,
    );

    const [
        agentError,
        setAgentError,
    ] = useState<
        string | null
    >(
        null,
    );


    async function askReconAI(): Promise<void> {
        if (
            !detail?.transaction_id
        ) {
            return;
        }

        const message =
            agentMessage.trim();

        if (
            !message
        ) {
            setAgentError(
                "Enter a question for ReconAI.",
            );

            return;
        }

        setAgentLoading(
            true,
        );

        setAgentError(
            null,
        );

        setAgentResponse(
            null,
        );

        try {
            const response =
                await fetch(
                    "/api/reconai/agent",
                    {
                        method: "POST",

                        cache: "no-store",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    message,

                                    transaction_id:
                                        detail.transaction_id,
                                },
                            ),
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
                    `Agent endpoint returned non-JSON (${response.status}).`,
                );
            }

            let payload:
                | AgentQueryResponse
                | {
                    detail?: string;
                };

            try {
                payload =
                    JSON.parse(
                        rawBody,
                    ) as
                    | AgentQueryResponse
                    | {
                        detail?: string;
                    };
            } catch {
                throw new Error(
                    "Agent endpoint returned malformed JSON.",
                );
            }

            if (
                !response.ok
            ) {
                throw new Error(
                    "detail" in payload &&
                        typeof payload.detail ===
                        "string"
                        ? payload.detail
                        : `Agent request failed (${response.status}).`,
                );
            }

            setAgentResponse(
                payload as AgentQueryResponse,
            );
        } catch (
        caught
        ) {
            console.error(
                "[ReconAI] Agent request failed:",
                caught,
            );

            setAgentError(
                caught instanceof Error
                    ? caught.message
                    : "Unable to query ReconAI.",
            );
        } finally {
            setAgentLoading(
                false,
            );
        }
    }


    function handleClose(): void {
        setAgentResponse(
            null,
        );

        setAgentError(
            null,
        );

        setAgentLoading(
            false,
        );

        setAgentMessage(
            DEFAULT_AGENT_MESSAGE,
        );

        onClose();
    }


    if (
        !open
    ) {
        return null;
    }


    return (
        <div
            className="fixed inset-0 z-50"
            role="dialog"
            aria-modal="true"
            aria-label="Exception investigation"
        >
            <button
                type="button"
                aria-label="Close investigation"
                onClick={
                    handleClose
                }
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            />

            <aside className="absolute bottom-0 right-0 top-0 w-full max-w-2xl overflow-y-auto border-l border-white/10 bg-[#0b0b0e] shadow-2xl">
                {/* ---------------------------------------------------- */}
                {/* HEADER */}
                {/* ---------------------------------------------------- */}

                <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0b0b0e]/95 px-6 py-5 backdrop-blur">
                    <div>
                        <p className="text-xs font-medium uppercase tracking-[0.2em] text-indigo-400">
                            Deterministic Investigation
                        </p>

                        <h2 className="mt-1 text-lg font-semibold text-white">
                            Exception Evidence
                        </h2>
                    </div>

                    <button
                        type="button"
                        onClick={
                            handleClose
                        }
                        className="rounded-lg border border-white/10 bg-white/[0.04] p-2 text-zinc-400 transition hover:bg-white/[0.08] hover:text-white"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                <div className="p-6">
                    {/* -------------------------------------------------- */}
                    {/* LOADING */}
                    {/* -------------------------------------------------- */}

                    {loading && (
                        <div className="flex min-h-[400px] flex-col items-center justify-center">
                            <Loader2 className="h-7 w-7 animate-spin text-indigo-400" />

                            <p className="mt-4 text-sm text-zinc-500">
                                Loading deterministic evidence...
                            </p>
                        </div>
                    )}

                    {/* -------------------------------------------------- */}
                    {/* INVESTIGATION ERROR */}
                    {/* -------------------------------------------------- */}

                    {!loading &&
                        error && (
                            <div className="rounded-xl border border-rose-500/20 bg-rose-500/[0.08] p-5">
                                <div className="flex gap-3">
                                    <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />

                                    <div>
                                        <p className="font-medium text-rose-300">
                                            Investigation failed
                                        </p>

                                        <p className="mt-1 text-sm leading-6 text-rose-300/70">
                                            {error}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                    {/* -------------------------------------------------- */}
                    {/* INVESTIGATION */}
                    {/* -------------------------------------------------- */}

                    {!loading &&
                        detail && (
                            <div className="space-y-5">
                                {/* -------------------------------------------- */}
                                {/* TRANSACTION SUMMARY */}
                                {/* -------------------------------------------- */}

                                <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
                                    <div className="flex flex-wrap items-start justify-between gap-4">
                                        <div>
                                            <p className="text-xs text-zinc-600">
                                                Transaction ID
                                            </p>

                                            <p className="mt-2 font-mono text-sm text-zinc-100">
                                                {detail.transaction_id ??
                                                    "—"}
                                            </p>
                                        </div>

                                        <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-300">
                                            {detail.status ??
                                                "UNKNOWN"}
                                        </span>
                                    </div>

                                    <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
                                        <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                            <p className="text-xs text-zinc-600">
                                                Amount Difference
                                            </p>

                                            <p className="mt-2 text-lg font-semibold text-white">
                                                {formatMoney(
                                                    detail.amount_difference,
                                                )}
                                            </p>
                                        </div>

                                        <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                            <p className="text-xs text-zinc-600">
                                                Confidence
                                            </p>

                                            <p className="mt-2 text-lg font-semibold text-white">
                                                {(
                                                    detail.confidence *
                                                    100
                                                ).toFixed(
                                                    1,
                                                )}
                                                %
                                            </p>
                                        </div>

                                        <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                            <p className="text-xs text-zinc-600">
                                                Method
                                            </p>

                                            <p className="mt-2 text-sm font-semibold text-white">
                                                {detail.method ??
                                                    "NONE"}
                                            </p>
                                        </div>
                                    </div>
                                </section>

                                {/* -------------------------------------------- */}
                                {/* DETERMINISTIC REASON */}
                                {/* -------------------------------------------- */}

                                <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
                                    <div className="mb-4 flex items-center gap-2">
                                        <Search className="h-4 w-4 text-indigo-400" />

                                        <h3 className="text-sm font-semibold text-white">
                                            Deterministic Reason
                                        </h3>
                                    </div>

                                    <p className="text-sm leading-6 text-zinc-400">
                                        {detail.reason ??
                                            "No reconciliation reason was recorded."}
                                    </p>
                                </section>

                                {/* -------------------------------------------- */}
                                {/* SOURCE EVIDENCE */}
                                {/* -------------------------------------------- */}

                                <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
                                    <div className="mb-4 flex items-center gap-2">
                                        <Database className="h-4 w-4 text-sky-400" />

                                        <h3 className="text-sm font-semibold text-white">
                                            Source Evidence
                                        </h3>
                                    </div>

                                    {Object.keys(
                                        detail.evidence,
                                    ).length ===
                                        0 ? (
                                        <p className="text-sm text-zinc-600">
                                            No additional evidence fields were recorded.
                                        </p>
                                    ) : (
                                        <div className="divide-y divide-white/[0.06] rounded-xl border border-white/[0.07]">
                                            {Object.entries(
                                                detail.evidence,
                                            ).map(
                                                ([
                                                    key,
                                                    value,
                                                ]) => (
                                                    <div
                                                        key={key}
                                                        className="grid gap-2 px-4 py-3 sm:grid-cols-[180px_1fr]"
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
                                    )}
                                </section>

                                {/* -------------------------------------------- */}
                                {/* HUMAN ACTION */}
                                {/* -------------------------------------------- */}

                                <section className="rounded-2xl border border-emerald-500/15 bg-emerald-500/[0.05] p-5">
                                    <div className="mb-3 flex items-center gap-2">
                                        <ShieldCheck className="h-4 w-4 text-emerald-400" />

                                        <h3 className="text-sm font-semibold text-emerald-300">
                                            Recommended Human Action
                                        </h3>
                                    </div>

                                    <p className="text-sm leading-6 text-zinc-400">
                                        {detail.recommended_action}
                                    </p>

                                    <div className="mt-4 flex items-center gap-2 text-xs text-emerald-400/70">
                                        <ArrowRight className="h-3.5 w-3.5" />

                                        No automatic financial mutation is performed.
                                    </div>
                                </section>

                                {/* -------------------------------------------- */}
                                {/* AUDIT COUNTS */}
                                {/* -------------------------------------------- */}

                                <section className="grid gap-3 sm:grid-cols-2">
                                    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
                                        <FileClock className="mb-4 h-4 w-4 text-zinc-500" />

                                        <p className="text-2xl font-semibold text-white">
                                            {detail.exception_history_count}
                                        </p>

                                        <p className="mt-1 text-xs text-zinc-600">
                                            Exception history events
                                        </p>
                                    </div>

                                    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5">
                                        <ShieldCheck className="mb-4 h-4 w-4 text-zinc-500" />

                                        <p className="text-2xl font-semibold text-white">
                                            {detail.audit_record_count}
                                        </p>

                                        <p className="mt-1 text-xs text-zinc-600">
                                            Immutable audit records
                                        </p>
                                    </div>
                                </section>

                                {/* -------------------------------------------- */}
                                {/* ASK RECONAI */}
                                {/* -------------------------------------------- */}

                                <section className="overflow-hidden rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/[0.09] to-violet-500/[0.04]">
                                    <div className="border-b border-indigo-500/10 p-5">
                                        <div className="flex items-start gap-3">
                                            <div className="rounded-xl border border-indigo-400/20 bg-indigo-500/10 p-2.5">
                                                <Sparkles className="h-5 w-5 text-indigo-300" />
                                            </div>

                                            <div>
                                                <h3 className="text-sm font-semibold text-white">
                                                    Ask ReconAI
                                                </h3>

                                                <p className="mt-1 text-xs leading-5 text-zinc-500">
                                                    ReconAI will use the selected transaction&apos;s
                                                    deterministic investigation tool before generating
                                                    an explanation.
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="p-5">
                                        <textarea
                                            rows={3}
                                            value={
                                                agentMessage
                                            }
                                            onChange={(
                                                event,
                                            ) => {
                                                setAgentMessage(
                                                    event.target.value,
                                                );
                                            }}
                                            placeholder="Ask ReconAI about this exception..."
                                            className="w-full resize-none rounded-xl border border-white/10 bg-black/30 p-4 text-sm leading-6 text-zinc-200 outline-none transition placeholder:text-zinc-700 focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/10"
                                        />

                                        <div className="mt-3 flex justify-end">
                                            <button
                                                type="button"
                                                disabled={
                                                    agentLoading ||
                                                    !agentMessage.trim()
                                                }
                                                onClick={() => {
                                                    void askReconAI();
                                                }}
                                                className="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
                                            >
                                                {agentLoading ? (
                                                    <>
                                                        <Loader2 className="h-4 w-4 animate-spin" />

                                                        Investigating...
                                                    </>
                                                ) : (
                                                    <>
                                                        <Send className="h-4 w-4" />

                                                        Ask ReconAI
                                                    </>
                                                )}
                                            </button>
                                        </div>

                                        {/* ---------------------------------------- */}
                                        {/* AGENT ERROR */}
                                        {/* ---------------------------------------- */}

                                        {agentError && (
                                            <div className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/[0.07] p-4">
                                                <div className="flex gap-3">
                                                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />

                                                    <p className="text-sm leading-6 text-rose-300">
                                                        {agentError}
                                                    </p>
                                                </div>
                                            </div>
                                        )}

                                        {/* ---------------------------------------- */}
                                        {/* AGENT RESPONSE */}
                                        {/* ---------------------------------------- */}

                                        {agentResponse && (
                                            <div className="mt-5 space-y-4">
                                                <div className="rounded-xl border border-white/10 bg-black/25 p-5">
                                                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                                                        <div className="flex items-center gap-2">
                                                            <Bot className="h-4 w-4 text-indigo-300" />

                                                            <span className="text-sm font-semibold text-white">
                                                                ReconAI Response
                                                            </span>
                                                        </div>

                                                        <span
                                                            className={`rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase ${agentResponse.ai_explanation_used
                                                                    ? "border-indigo-500/20 bg-indigo-500/10 text-indigo-300"
                                                                    : "border-amber-500/20 bg-amber-500/10 text-amber-300"
                                                                }`}
                                                        >
                                                            {providerLabel(
                                                                agentResponse,
                                                            )}
                                                        </span>
                                                    </div>

                                                    <p className="whitespace-pre-wrap text-sm leading-7 text-zinc-300">
                                                        {agentResponse.answer}
                                                    </p>
                                                </div>

                                                {/* ------------------------------------ */}
                                                {/* TOOL PROVENANCE */}
                                                {/* ------------------------------------ */}

                                                <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                                                    <div className="mb-3 flex items-center gap-2">
                                                        <Wrench className="h-4 w-4 text-zinc-500" />

                                                        <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                                                            Evidence Provenance
                                                        </p>
                                                    </div>

                                                    <div className="space-y-3">
                                                        <div className="flex items-center justify-between gap-4">
                                                            <span className="text-xs text-zinc-600">
                                                                Deterministic tools
                                                            </span>

                                                            <span className="font-mono text-xs text-zinc-300">
                                                                {agentResponse.tools_used.length >
                                                                    0
                                                                    ? agentResponse.tools_used.join(
                                                                        ", ",
                                                                    )
                                                                    : "none"}
                                                            </span>
                                                        </div>

                                                        <div className="flex items-center justify-between gap-4">
                                                            <span className="text-xs text-zinc-600">
                                                                Provider
                                                            </span>

                                                            <span className="max-w-[320px] break-all text-right font-mono text-xs text-zinc-400">
                                                                {agentResponse.provider_status}
                                                            </span>
                                                        </div>

                                                        <div className="flex items-center justify-between gap-4">
                                                            <span className="text-xs text-zinc-600">
                                                                Financial state mutated
                                                            </span>

                                                            <span
                                                                className={`inline-flex items-center gap-1.5 text-xs font-medium ${agentResponse.financial_state_mutated
                                                                        ? "text-rose-400"
                                                                        : "text-emerald-400"
                                                                    }`}
                                                            >
                                                                {agentResponse.financial_state_mutated ? (
                                                                    <>
                                                                        <AlertTriangle className="h-3.5 w-3.5" />

                                                                        YES
                                                                    </>
                                                                ) : (
                                                                    <>
                                                                        <CheckCircle2 className="h-3.5 w-3.5" />

                                                                        NO
                                                                    </>
                                                                )}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {!agentResponse.ai_explanation_used && (
                                                    <div className="rounded-xl border border-amber-500/15 bg-amber-500/[0.05] p-4">
                                                        <p className="text-xs leading-5 text-amber-200/70">
                                                            The external AI provider was unavailable.
                                                            ReconAI therefore returned deterministic
                                                            finance evidence directly. The investigation
                                                            remains usable and no financial conclusion was
                                                            invented.
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </section>

                                {/* -------------------------------------------- */}
                                {/* SAFETY FOOTNOTE */}
                                {/* -------------------------------------------- */}

                                <section className="rounded-xl border border-indigo-500/10 bg-indigo-500/[0.04] p-4">
                                    <p className="text-xs leading-5 text-indigo-300/70">
                                        Financial truth comes from deterministic reconciliation
                                        tools. AI is restricted to explanation and investigation
                                        assistance.
                                    </p>
                                </section>
                            </div>
                        )}
                </div>
            </aside>
        </div>
    );
}