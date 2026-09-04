"use client";

import {
    AlertTriangle,
    CheckCircle2,
    CircleAlert,
    FlaskConical,
    Loader2,
    Play,
    RefreshCw,
    ShieldCheck,
    WalletCards,
    XCircle,
} from "lucide-react";

import {
    useState,
} from "react";

import type {
    RazorpayDemoResult,
    RazorpayDemoTransaction,
} from "@/lib/types";


function formatMoney(
    value: number,
    currency = "INR",
): string {
    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency,
            maximumFractionDigits: 2,
        },
    ).format(
        value,
    );
}


function statusClasses(
    status: string,
): string {
    switch (
    status
    ) {
        case "MATCHED":
        case "FUZZY_MATCHED":
            return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";

        case "AMOUNT_MISMATCH":
            return "border-amber-500/20 bg-amber-500/10 text-amber-300";

        case "AMBIGUOUS":
            return "border-violet-500/20 bg-violet-500/10 text-violet-300";

        case "MISSING_LEDGER":
        case "MISSING_PAYMENT":
            return "border-sky-500/20 bg-sky-500/10 text-sky-300";

        default:
            return "border-white/10 bg-white/5 text-zinc-300";
    }
}


function scenarioLabel(
    status: string,
): string {
    switch (
    status
    ) {
        case "MATCHED":
            return "Exact merchant evidence";

        case "AMOUNT_MISMATCH":
            return "Injected ledger amount mismatch";

        case "MISSING_LEDGER":
            return "Injected missing merchant ledger";

        case "AMBIGUOUS":
            return "Injected competing ledger candidates";

        case "MISSING_PAYMENT":
            return "Supplemental source-only evidence";

        default:
            return "Controlled reconciliation scenario";
    }
}


function scenarioDescription(
    status: string,
): string {
    switch (
    status
    ) {
        case "MATCHED":
            return (
                "The Razorpay payment, controlled merchant ledger "
                + "and settlement fixture agree."
            );

        case "AMOUNT_MISMATCH":
            return (
                "The controlled merchant ledger amount is deliberately "
                + "different from the Razorpay payment amount."
            );

        case "MISSING_LEDGER":
            return (
                "The Razorpay payment is real, but the demo deliberately "
                + "omits the merchant ledger row."
            );

        case "AMBIGUOUS":
            return (
                "The demo creates competing merchant ledger candidates, "
                + "so ReconAI refuses to silently choose one."
            );

        case "MISSING_PAYMENT":
            return (
                "A supplemental source record exists without a matching "
                + "canonical payment decision."
            );

        default:
            return (
                "The merchant-side evidence is controlled to exercise "
                + "a deterministic reconciliation outcome."
            );
    }
}


export function RazorpayDemoPanel() {
    const [
        result,
        setResult,
    ] = useState<
        RazorpayDemoResult | null
    >(
        null,
    );

    const [
        selected,
        setSelected,
    ] = useState<
        RazorpayDemoTransaction | null
    >(
        null,
    );

    const [
        running,
        setRunning,
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


    async function runDemo(): Promise<void> {
        setRunning(
            true,
        );

        setError(
            null,
        );

        setSelected(
            null,
        );

        try {
            const response =
                await fetch(
                    "/api/reconai/razorpay-demo",
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
                    `Razorpay demo returned non-JSON (${response.status}).`,
                );
            }

            const payload =
                JSON.parse(
                    rawBody,
                ) as
                | RazorpayDemoResult
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
                        : "Razorpay demo failed.",
                );
            }

            const demoResult =
                payload as RazorpayDemoResult;

            setResult(
                demoResult,
            );

            setSelected(
                demoResult.transactions[
                0
                ] ??
                null,
            );
        } catch (
        caught
        ) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : "Unable to run Razorpay demo.",
            );
        } finally {
            setRunning(
                false,
            );
        }
    }


    return (
        <section className="overflow-hidden rounded-2xl border border-sky-500/20 bg-gradient-to-br from-sky-500/[0.07] via-white/[0.025] to-indigo-500/[0.04]">

            {/* ================================================== */}
            {/* HEADER */}
            {/* ================================================== */}

            <div className="flex flex-col gap-5 border-b border-white/10 p-6 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex gap-4">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-sky-400/20 bg-sky-500/10">
                        <WalletCards className="h-5 w-5 text-sky-300" />
                    </div>

                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-base font-semibold text-white">
                                Razorpay Working Reconciliation Demo
                            </h2>

                            <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-2.5 py-1 text-[10px] font-medium uppercase text-sky-300">
                                Test Mode
                            </span>
                        </div>

                        <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">
                            Fetch current captured Razorpay Test Mode payments
                            and reconcile them through the real ReconAI
                            deterministic engine.
                        </p>
                    </div>
                </div>

                <button
                    type="button"
                    disabled={
                        running
                    }
                    onClick={() => {
                        void runDemo();
                    }}
                    className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-sky-500 px-5 py-3 text-sm font-medium text-white transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {running ? (
                        <>
                            <Loader2 className="h-4 w-4 animate-spin" />

                            Reconciling...
                        </>
                    ) : result ? (
                        <>
                            <RefreshCw className="h-4 w-4" />

                            Run Again
                        </>
                    ) : (
                        <>
                            <Play className="h-4 w-4" />

                            Run Razorpay Demo
                        </>
                    )}
                </button>
            </div>


            {/* ================================================== */}
            {/* SOURCE DISCLOSURE */}
            {/* ================================================== */}

            <div className="grid gap-px border-b border-white/10 bg-white/10 sm:grid-cols-3">
                <div className="bg-[#0d0d11] p-4">
                    <p className="text-[10px] uppercase tracking-wider text-zinc-600">
                        Payment Source
                    </p>

                    <p className="mt-2 text-sm font-medium text-sky-300">
                        Razorpay Test Mode
                    </p>

                    <p className="mt-1 text-xs text-zinc-600">
                        Real payment records fetched from Razorpay API
                    </p>
                </div>

                <div className="bg-[#0d0d11] p-4">
                    <p className="text-[10px] uppercase tracking-wider text-zinc-600">
                        Merchant Ledger
                    </p>

                    <p className="mt-2 text-sm font-medium text-zinc-300">
                        Controlled Fixture
                    </p>

                    <p className="mt-1 text-xs text-zinc-600">
                        Merchant-side evidence used to inject demo scenarios
                    </p>
                </div>

                <div className="bg-[#0d0d11] p-4">
                    <p className="text-[10px] uppercase tracking-wider text-zinc-600">
                        Settlement Source
                    </p>

                    <p className="mt-2 text-sm font-medium text-amber-300">
                        Controlled Synthetic Fixture
                    </p>

                    <p className="mt-1 text-xs text-zinc-600">
                        Used because Test Mode settlement evidence is unavailable
                    </p>
                </div>
            </div>


            <div className="p-6">

                {/* ================================================== */}
                {/* DEMO DISCLOSURE */}
                {/* ================================================== */}

                <div className="mb-5 rounded-xl border border-violet-500/15 bg-violet-500/[0.05] p-4">
                    <div className="flex gap-3">
                        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-violet-300" />

                        <div>
                            <p className="text-sm font-medium text-violet-200">
                                Controlled scenario injection
                            </p>

                            <p className="mt-1 text-xs leading-5 text-zinc-500">
                                Razorpay Test Mode payment records remain real
                                and unmodified. Exception scenarios are
                                intentionally introduced only in controlled
                                merchant-side evidence so ReconAI can
                                demonstrate safe reconciliation behavior.
                            </p>
                        </div>
                    </div>
                </div>


                {/* ================================================== */}
                {/* ERROR */}
                {/* ================================================== */}

                {error && (
                    <div className="rounded-xl border border-rose-500/20 bg-rose-500/[0.06] p-4">
                        <div className="flex gap-3">
                            <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />

                            <div>
                                <p className="text-sm font-medium text-rose-300">
                                    Razorpay demo failed
                                </p>

                                <p className="mt-1 text-xs leading-5 text-rose-300/70">
                                    {error}
                                </p>
                            </div>
                        </div>
                    </div>
                )}


                {/* ================================================== */}
                {/* INITIAL STATE */}
                {/* ================================================== */}

                {!result &&
                    !running &&
                    !error && (
                        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-white/10 py-12 text-center">
                            <FlaskConical className="h-7 w-7 text-zinc-700" />

                            <p className="mt-4 text-sm font-medium text-zinc-300">
                                Ready for live Test Mode reconciliation
                            </p>

                            <p className="mt-2 max-w-lg text-xs leading-5 text-zinc-600">
                                ReconAI will fetch current Razorpay payments,
                                select four captured payments deterministically,
                                attach controlled merchant evidence and run the
                                real reconciliation engine.
                            </p>
                        </div>
                    )}


                {/* ================================================== */}
                {/* RESULTS */}
                {/* ================================================== */}

                {result && (
                    <div className="space-y-5">

                        {/* ------------------------------------------ */}
                        {/* METRICS */}
                        {/* ------------------------------------------ */}

                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                            <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                <p className="text-xs text-zinc-600">
                                    Razorpay Ingested
                                </p>

                                <p className="mt-2 text-2xl font-semibold text-white">
                                    {
                                        result.summary
                                            .razorpay_payments_ingested
                                    }
                                </p>
                            </div>


                            <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                <p className="text-xs text-zinc-600">
                                    Captured / Eligible
                                </p>

                                <p className="mt-2 text-2xl font-semibold text-white">
                                    {
                                        result.summary
                                            .captured_eligible
                                    }
                                </p>
                            </div>


                            <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                <p className="text-xs text-zinc-600">
                                    Demo Transactions
                                </p>

                                <p className="mt-2 text-2xl font-semibold text-white">
                                    {
                                        result.summary
                                            .demo_transactions
                                    }
                                </p>
                            </div>


                            <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                <p className="text-xs text-zinc-600">
                                    Resolved
                                </p>

                                <p className="mt-2 text-2xl font-semibold text-emerald-300">
                                    {
                                        result.summary
                                            .automatically_resolved
                                    }
                                </p>
                            </div>


                            <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                                <p className="text-xs text-zinc-600">
                                    Exceptions
                                </p>

                                <p className="mt-2 text-2xl font-semibold text-amber-300">
                                    {
                                        result.summary
                                            .canonical_exceptions
                                    }
                                </p>
                            </div>
                        </div>


                        {/* ------------------------------------------ */}
                        {/* TABLE */}
                        {/* ------------------------------------------ */}

                        <div className="overflow-hidden rounded-xl border border-white/10">
                            <div className="overflow-x-auto">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="border-b border-white/10 bg-black/20 text-xs uppercase tracking-wider text-zinc-600">
                                            <th className="px-5 py-4 font-medium">
                                                Razorpay Payment
                                            </th>

                                            <th className="px-5 py-4 font-medium">
                                                Amount
                                            </th>

                                            <th className="px-5 py-4 font-medium">
                                                Demo Scenario
                                            </th>

                                            <th className="px-5 py-4 font-medium">
                                                ReconAI Result
                                            </th>

                                            <th className="px-5 py-4 font-medium">
                                                Evidence
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {result.transactions.map(
                                            (
                                                transaction,
                                            ) => (
                                                <tr
                                                    key={
                                                        transaction.transaction_id
                                                    }
                                                    onClick={() => {
                                                        setSelected(
                                                            transaction,
                                                        );
                                                    }}
                                                    className="cursor-pointer border-b border-white/[0.06] transition last:border-none hover:bg-sky-500/[0.04]"
                                                >
                                                    <td className="px-5 py-4">
                                                        <p className="font-mono text-xs text-zinc-300">
                                                            {
                                                                transaction.payment_id
                                                            }
                                                        </p>

                                                        <p className="mt-1 font-mono text-[10px] text-zinc-700">
                                                            {
                                                                transaction.transaction_id
                                                            }
                                                        </p>
                                                    </td>

                                                    <td className="whitespace-nowrap px-5 py-4 text-sm text-zinc-300">
                                                        {
                                                            formatMoney(
                                                                transaction.payment_amount,
                                                                transaction.currency,
                                                            )
                                                        }
                                                    </td>

                                                    <td className="min-w-[230px] px-5 py-4">
                                                        <p className="text-xs font-medium text-zinc-300">
                                                            {
                                                                scenarioLabel(
                                                                    transaction.expected_status,
                                                                )
                                                            }
                                                        </p>

                                                        <p className="mt-1 text-[11px] leading-4 text-zinc-600">
                                                            {
                                                                scenarioDescription(
                                                                    transaction.expected_status,
                                                                )
                                                            }
                                                        </p>
                                                    </td>

                                                    <td className="px-5 py-4">
                                                        <span
                                                            className={`rounded-full border px-2.5 py-1 text-[10px] font-medium ${statusClasses(
                                                                transaction.actual_status,
                                                            )}`}
                                                        >
                                                            {
                                                                transaction.actual_status
                                                            }
                                                        </span>
                                                    </td>

                                                    <td className="px-5 py-4 text-xs font-medium text-sky-300">
                                                        Inspect
                                                    </td>
                                                </tr>
                                            ),
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>


                        {/* ------------------------------------------ */}
                        {/* SELECTED TRANSACTION */}
                        {/* ------------------------------------------ */}

                        {selected && (
                            <div className="rounded-xl border border-white/10 bg-black/20 p-5">
                                <div className="flex flex-wrap items-start justify-between gap-4">
                                    <div>
                                        <p className="text-xs uppercase tracking-wider text-zinc-600">
                                            Reconciliation Evidence
                                        </p>

                                        <p className="mt-2 font-mono text-sm text-white">
                                            {
                                                selected.payment_id
                                            }
                                        </p>
                                    </div>

                                    <span
                                        className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClasses(
                                            selected.actual_status,
                                        )}`}
                                    >
                                        {
                                            selected.actual_status
                                        }
                                    </span>
                                </div>


                                {/* SCENARIO */}

                                <div className="mt-5 rounded-lg border border-violet-500/15 bg-violet-500/[0.035] p-4">
                                    <p className="text-[10px] uppercase tracking-wider text-violet-400">
                                        Injected Demo Scenario
                                    </p>

                                    <p className="mt-2 text-sm font-medium text-zinc-200">
                                        {
                                            scenarioLabel(
                                                selected.expected_status,
                                            )
                                        }
                                    </p>

                                    <p className="mt-1 text-xs leading-5 text-zinc-500">
                                        {
                                            scenarioDescription(
                                                selected.expected_status,
                                            )
                                        }
                                    </p>
                                </div>


                                {/* SOURCE EVIDENCE */}

                                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Razorpay Payment
                                        </p>

                                        <p className="mt-2 break-all font-mono text-xs text-zinc-300">
                                            {
                                                selected.payment_id
                                            }
                                        </p>

                                        <p className="mt-2 text-[10px] text-sky-400">
                                            Real Test Mode evidence
                                        </p>
                                    </div>


                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Merchant Ledger
                                        </p>

                                        <p className="mt-2 break-all font-mono text-xs text-zinc-300">
                                            {
                                                selected.ledger_id ??
                                                "No ledger evidence"
                                            }
                                        </p>

                                        <p className="mt-2 text-[10px] text-zinc-600">
                                            Controlled fixture
                                        </p>
                                    </div>


                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Settlement
                                        </p>

                                        <p className="mt-2 break-all font-mono text-xs text-zinc-300">
                                            {
                                                selected.settlement_id ??
                                                "No settlement evidence"
                                            }
                                        </p>

                                        <p className="mt-2 text-[10px] text-amber-400">
                                            Controlled synthetic fixture
                                        </p>
                                    </div>


                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Amount Difference
                                        </p>

                                        <p className="mt-2 text-sm font-medium text-white">
                                            {
                                                formatMoney(
                                                    selected.amount_difference,
                                                    selected.currency,
                                                )
                                            }
                                        </p>

                                        <p className="mt-2 text-[10px] text-zinc-600">
                                            Deterministically calculated
                                        </p>
                                    </div>
                                </div>


                                {/* ENGINE DECISION */}

                                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Method
                                        </p>

                                        <p className="mt-2 text-xs font-medium text-zinc-300">
                                            {
                                                selected.method
                                            }
                                        </p>
                                    </div>

                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Confidence
                                        </p>

                                        <p className="mt-2 text-xs font-medium text-zinc-300">
                                            {
                                                (
                                                    selected.confidence *
                                                    100
                                                ).toFixed(
                                                    1,
                                                )
                                            }
                                            %
                                        </p>
                                    </div>

                                    <div className="rounded-lg border border-white/[0.06] p-3">
                                        <p className="text-[10px] uppercase tracking-wider text-zinc-700">
                                            Expected Demo Outcome
                                        </p>

                                        <p className="mt-2 text-xs font-medium text-zinc-300">
                                            {
                                                selected.expected_status
                                            }
                                        </p>
                                    </div>
                                </div>


                                {/* REASON */}

                                <div className="mt-4 rounded-lg border border-white/[0.06] p-4">
                                    <p className="text-xs font-medium text-zinc-400">
                                        Deterministic ReconAI reason
                                    </p>

                                    <p className="mt-2 text-sm leading-6 text-zinc-500">
                                        {
                                            selected.reason
                                        }
                                    </p>
                                </div>
                            </div>
                        )}


                        {/* ------------------------------------------ */}
                        {/* SAFETY */}
                        {/* ------------------------------------------ */}

                        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-emerald-500/10 bg-emerald-500/[0.035] p-4">
                            <div className="flex items-center gap-2">
                                {result.summary.passed ? (
                                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                                ) : (
                                    <AlertTriangle className="h-4 w-4 text-rose-400" />
                                )}

                                <span className="text-xs text-zinc-400">
                                    Demo integrity{" "}
                                    {
                                        result.summary.passed
                                            ? "PASS"
                                            : "FAIL"
                                    }
                                </span>
                            </div>

                            <div className="flex items-center gap-2 text-xs text-zinc-500">
                                <ShieldCheck className="h-4 w-4 text-emerald-400" />

                                {
                                    result.summary
                                        .unsafe_duplicate_resolutions
                                }{" "}
                                unsafe duplicate resolutions
                            </div>

                            <div className="flex items-center gap-2 text-xs text-zinc-500">
                                <CircleAlert className="h-4 w-4 text-sky-400" />

                                Financial state mutated:{" "}
                                {
                                    result.financial_state_mutated
                                        ? "YES"
                                        : "NO"
                                }
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </section>
    );
}