"use client";

import {
    Activity,
    Bot,
    CheckCircle2,
    FileSearch,
    Loader2,
    MessageSquareText,
    Send,
    ShieldCheck,
    Sparkles,
    TriangleAlert,
    WalletCards,
    Wrench,
} from "lucide-react";

import {
    useState,
} from "react";

import type {
    AgentQueryResponse,
    FinanceAgentAction,
} from "@/lib/types";


interface QuickAction {
    label: string;

    description: string;

    action: FinanceAgentAction;

    icon: typeof Activity;
}


const QUICK_ACTIONS: QuickAction[] = [
    {
        label:
            "Batch Summary",

        description:
            "Reconciliation health and metrics",

        action:
            "batch_summary",

        icon:
            Activity,
    },
    {
        label:
            "Finance Attention",

        description:
            "What needs operations attention",

        action:
            "finance_ops_summary",

        icon:
            WalletCards,
    },
    {
        label:
            "High-Value Exceptions",

        description:
            "Largest financial discrepancies",

        action:
            "high_value_exceptions",

        icon:
            FileSearch,
    },
    {
        label:
            "Verify Audit",

        description:
            "Cryptographic chain verification",

        action:
            "verify_audit_chain",

        icon:
            ShieldCheck,
    },
];


function prettyEvidence(
    value: unknown,
): string {
    return JSON.stringify(
        value,
        null,
        2,
    );
}


export function FinanceControllerAgent() {
    const [
        message,
        setMessage,
    ] = useState(
        "",
    );

    const [
        response,
        setResponse,
    ] = useState<
        AgentQueryResponse | null
    >(
        null,
    );

    const [
        loading,
        setLoading,
    ] = useState(
        false,
    );

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(
        null,
    );


    async function sendRequest(
        payload: {
            message?: string;
            action?: FinanceAgentAction;
            limit?: number;
        },
    ): Promise<void> {
        setLoading(
            true,
        );

        setError(
            null,
        );

        setResponse(
            null,
        );

        try {
            const apiResponse =
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
                                payload,
                            ),
                    },
                );

            const contentType =
                apiResponse.headers.get(
                    "content-type",
                ) ?? "";

            const rawBody =
                await apiResponse.text();

            if (
                !contentType.includes(
                    "application/json",
                )
            ) {
                throw new Error(
                    `Agent endpoint returned non-JSON (${apiResponse.status}).`,
                );
            }

            const parsed =
                JSON.parse(
                    rawBody,
                ) as
                | AgentQueryResponse
                | {
                    detail?: string;
                };

            if (
                !apiResponse.ok
            ) {
                throw new Error(
                    "detail" in parsed &&
                        typeof parsed.detail ===
                        "string"
                        ? parsed.detail
                        : `Agent request failed (${apiResponse.status}).`,
                );
            }

            setResponse(
                parsed as AgentQueryResponse,
            );
        } catch (
        caught
        ) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : "Unable to query ReconAI.",
            );
        } finally {
            setLoading(
                false,
            );
        }
    }


    async function submitFreeForm(): Promise<void> {
        const normalized =
            message.trim();

        if (
            !normalized
        ) {
            return;
        }

        await sendRequest(
            {
                message:
                    normalized,
            },
        );
    }


    async function runQuickAction(
        action: FinanceAgentAction,
    ): Promise<void> {
        await sendRequest(
            {
                action,
                limit: 5,
            },
        );
    }


    return (
        <section className="overflow-hidden rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/[0.08] via-white/[0.025] to-violet-500/[0.04]">
            {/* HEADER */}

            <div className="border-b border-white/10 p-6">
                <div className="flex items-start gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-400/20 bg-indigo-500/10">
                        <Sparkles className="h-5 w-5 text-indigo-300" />
                    </div>

                    <div>
                        <h2 className="text-base font-semibold text-white">
                            Finance Controller Agent
                        </h2>

                        <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">
                            Ask batch-level finance questions or run deterministic
                            controller actions. Financial truth always comes from
                            registered ReconAI tools.
                        </p>
                    </div>
                </div>
            </div>

            <div className="p-6">
                {/* QUICK ACTIONS */}

                <div>
                    <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-600">
                        Deterministic Quick Actions
                    </p>

                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        {QUICK_ACTIONS.map(
                            ({
                                label,
                                description,
                                action,
                                icon: Icon,
                            }) => (
                                <button
                                    key={
                                        action
                                    }
                                    type="button"
                                    disabled={
                                        loading
                                    }
                                    onClick={() => {
                                        void runQuickAction(
                                            action,
                                        );
                                    }}
                                    className="group rounded-xl border border-white/[0.07] bg-black/20 p-4 text-left transition hover:border-indigo-500/30 hover:bg-indigo-500/[0.07] disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    <Icon className="h-4 w-4 text-zinc-500 transition group-hover:text-indigo-300" />

                                    <p className="mt-4 text-sm font-medium text-zinc-200">
                                        {label}
                                    </p>

                                    <p className="mt-1 text-xs leading-5 text-zinc-600">
                                        {description}
                                    </p>
                                </button>
                            ),
                        )}
                    </div>
                </div>

                {/* FREE FORM */}

                <div className="mt-6">
                    <div className="mb-3 flex items-center gap-2">
                        <MessageSquareText className="h-4 w-4 text-zinc-500" />

                        <p className="text-xs font-medium uppercase tracking-wider text-zinc-600">
                            Ask ReconAI
                        </p>
                    </div>

                    <div className="rounded-xl border border-white/10 bg-black/25 p-3">
                        <textarea
                            value={
                                message
                            }
                            onChange={(
                                event,
                            ) => {
                                setMessage(
                                    event.target.value,
                                );
                            }}
                            rows={3}
                            placeholder='Try: "Summarize this reconciliation batch"'
                            className="w-full resize-none bg-transparent p-2 text-sm leading-6 text-zinc-200 outline-none placeholder:text-zinc-700"
                        />

                        <div className="mt-2 flex items-center justify-between gap-4 border-t border-white/[0.06] pt-3">
                            <p className="text-xs text-zinc-700">
                                Free-form reasoning uses the configured AI provider.
                            </p>

                            <button
                                type="button"
                                disabled={
                                    loading ||
                                    !message.trim()
                                }
                                onClick={() => {
                                    void submitFreeForm();
                                }}
                                className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-xs font-medium text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="h-3.5 w-3.5 animate-spin" />

                                        Running...
                                    </>
                                ) : (
                                    <>
                                        <Send className="h-3.5 w-3.5" />

                                        Ask ReconAI
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                {/* ERROR */}

                {error && (
                    <div className="mt-5 rounded-xl border border-rose-500/20 bg-rose-500/[0.06] p-4">
                        <div className="flex gap-3">
                            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />

                            <div>
                                <p className="text-sm font-medium text-rose-300">
                                    ReconAI request failed
                                </p>

                                <p className="mt-1 text-xs leading-5 text-rose-300/70">
                                    {error}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* RESPONSE */}

                {response && (
                    <div className="mt-6 space-y-4">
                        <div className="rounded-xl border border-white/10 bg-black/25 p-5">
                            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                                <div className="flex items-center gap-2">
                                    <Bot className="h-4 w-4 text-indigo-300" />

                                    <p className="text-sm font-semibold text-white">
                                        ReconAI Response
                                    </p>
                                </div>

                                <span
                                    className={`rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase ${response.success
                                            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                                            : "border-amber-500/20 bg-amber-500/10 text-amber-300"
                                        }`}
                                >
                                    {response.provider_status}
                                </span>
                            </div>

                            <p className="whitespace-pre-wrap text-sm leading-7 text-zinc-300">
                                {response.answer}
                            </p>
                        </div>

                        {/* PROVENANCE */}

                        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                            <div className="mb-4 flex items-center gap-2">
                                <Wrench className="h-4 w-4 text-zinc-500" />

                                <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                                    Evidence Provenance
                                </p>
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center justify-between gap-4">
                                    <span className="text-xs text-zinc-600">
                                        Tools executed
                                    </span>

                                    <span className="max-w-[65%] break-all text-right font-mono text-xs text-zinc-300">
                                        {response.tools_used.length >
                                            0
                                            ? response.tools_used.join(
                                                ", ",
                                            )
                                            : "none"}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between gap-4">
                                    <span className="text-xs text-zinc-600">
                                        AI explanation used
                                    </span>

                                    <span className="text-xs text-zinc-300">
                                        {response.ai_explanation_used
                                            ? "YES"
                                            : "NO"}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between gap-4">
                                    <span className="text-xs text-zinc-600">
                                        Financial state mutated
                                    </span>

                                    <span
                                        className={`inline-flex items-center gap-1.5 text-xs font-medium ${response.financial_state_mutated
                                                ? "text-rose-400"
                                                : "text-emerald-400"
                                            }`}
                                    >
                                        {response.financial_state_mutated ? (
                                            <>
                                                <TriangleAlert className="h-3.5 w-3.5" />

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

                            {response.deterministic_evidence !==
                                null && (
                                    <details className="mt-4 border-t border-white/[0.06] pt-4">
                                        <summary className="cursor-pointer text-xs font-medium text-zinc-500 transition hover:text-zinc-300">
                                            View deterministic evidence
                                        </summary>

                                        <pre className="mt-3 max-h-96 overflow-auto rounded-lg border border-white/[0.07] bg-black/30 p-4 text-xs leading-5 text-zinc-400">
                                            {prettyEvidence(
                                                response.deterministic_evidence,
                                            )}
                                        </pre>
                                    </details>
                                )}
                        </div>
                    </div>
                )}

                {/* SAFETY */}

                <div className="mt-6 flex gap-3 rounded-xl border border-emerald-500/10 bg-emerald-500/[0.035] p-4">
                    <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />

                    <p className="text-xs leading-5 text-zinc-500">
                        The Finance Controller Agent may inspect and explain
                        reconciliation evidence, but it cannot modify financial
                        records or the immutable audit chain.
                    </p>
                </div>
            </div>
        </section>
    );
}