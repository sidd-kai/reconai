import {
    Activity,
    Database,
    ShieldCheck,
    TriangleAlert,
} from "lucide-react";

import {
    ExceptionBreakdown,
} from "@/components/exception-breakdown";

import {
    ExceptionExplorer,
} from "@/components/exception-explorer";

import {
    FinanceControllerAgent,
} from "@/components/finance-controller-agent";

import {
    HighValueExceptions,
} from "@/components/high-value-exceptions";

import {
    IntegrityPanel,
} from "@/components/integrity-panel";

import {
    MetricCard,
} from "@/components/metric-card";

import {
    PerformancePanel,
} from "@/components/performance-panel";

import {
    RazorpayDemoPanel,
} from "@/components/razorpay-demo-panel";

import {
    RazorpayPanel,
} from "@/components/razorpay-panel";

import {
    getDashboardData,
} from "@/lib/api";


function formatPercent(
    value: number,
): string {
    const percentage =
        Math.abs(
            value,
        ) <= 1
            ? value * 100
            : value;

    return `${percentage.toFixed(2)}%`;
}


function formatThroughput(
    value: number,
): string {
    return `${value.toFixed(2)}/s`;
}


export default async function HomePage() {
    const data =
        await getDashboardData();

    const {
        summary,
        benchmark,
        exceptions,
        highValueExceptions,
        audit,
        razorpay,
    } = data;


    return (
        <main className="min-h-screen bg-[#07070a] text-zinc-100">
            <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">

                {/* ================================================== */}
                {/* HEADER */}
                {/* ================================================== */}

                <header className="mb-6">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                        <div>
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-violet-500/20 bg-violet-500/10">
                                    <Activity className="h-5 w-5 text-violet-300" />
                                </div>

                                <div>
                                    <h1 className="text-2xl font-semibold tracking-tight text-white">
                                        ReconAI
                                    </h1>

                                    <p className="mt-1 text-sm text-zinc-500">
                                        AI Finance Controller · Multi-Source Reconciliation
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full border border-violet-500/20 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-300">
                                Razorpay Buildathon
                            </span>

                            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-500">
                                Deterministic Finance Engine
                            </span>
                        </div>
                    </div>
                </header>


                {/* ================================================== */}
                {/* EVALUATION ENVIRONMENT */}
                {/* ================================================== */}

                <section className="mb-5 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                            <p className="text-sm font-medium text-white">
                                Evaluation Environment
                            </p>

                            <p className="mt-1 max-w-4xl text-xs leading-5 text-zinc-500">
                                Core reconciliation metrics are measured on the
                                controlled 1,000-transaction synthetic benchmark.
                                Razorpay Test Mode is demonstrated independently
                                using real payment evidence and controlled
                                merchant-side reconciliation fixtures.
                            </p>
                        </div>

                        <div className="flex flex-wrap gap-2">
                            <span className="rounded-lg border border-white/[0.07] bg-black/20 px-3 py-2 text-xs text-zinc-400">
                                Synthetic Benchmark · 1,000 Transactions
                            </span>

                            <span className="rounded-lg border border-sky-500/20 bg-sky-500/[0.06] px-3 py-2 text-xs text-sky-300">
                                Razorpay · Test Mode
                            </span>
                        </div>
                    </div>
                </section>


                {/* ================================================== */}
                {/* PRIMARY METRICS */}
                {/* ================================================== */}

                <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard
                        title="Match Rate"
                        value={
                            formatPercent(
                                summary.match_rate,
                            )
                        }
                        subtitle={`${summary.resolved.toLocaleString()} automatically reconciled`}
                        icon={
                            <Activity className="h-4 w-4" />
                        }
                    />

                    <MetricCard
                        title="Exceptions"
                        value={
                            summary.exceptions.toLocaleString()
                        }
                        subtitle={`${formatPercent(
                            summary.exception_rate,
                        )} exception rate`}
                        icon={
                            <TriangleAlert className="h-4 w-4" />
                        }
                    />

                    <MetricCard
                        title="Engine Throughput"
                        value={
                            formatThroughput(
                                benchmark.median_records_per_second,
                            )
                        }
                        subtitle="Median canonical records / second"
                        icon={
                            <Database className="h-4 w-4" />
                        }
                    />

                    <MetricCard
                        title="Integrity"
                        value={
                            summary.integrity_passed
                                ? "PASS"
                                : "FAIL"
                        }
                        subtitle="Deterministic reconciliation integrity"
                        icon={
                            <ShieldCheck className="h-4 w-4" />
                        }
                    />
                </section>


                {/* ================================================== */}
                {/* QUALITY METRICS */}
                {/* ================================================== */}

                <section className="mt-4 grid gap-4 sm:grid-cols-3">
                    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
                        <p className="text-xs uppercase tracking-wider text-zinc-600">
                            Precision
                        </p>

                        <p className="mt-3 text-2xl font-semibold text-white">
                            {formatPercent(
                                summary.precision,
                            )}
                        </p>

                        <p className="mt-2 text-xs text-zinc-600">
                            Benchmark classification precision
                        </p>
                    </div>


                    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
                        <p className="text-xs uppercase tracking-wider text-zinc-600">
                            Recall
                        </p>

                        <p className="mt-3 text-2xl font-semibold text-white">
                            {formatPercent(
                                summary.recall,
                            )}
                        </p>

                        <p className="mt-2 text-xs text-zinc-600">
                            Benchmark classification recall
                        </p>
                    </div>


                    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
                        <p className="text-xs uppercase tracking-wider text-zinc-600">
                            F1 Score
                        </p>

                        <p className="mt-3 text-2xl font-semibold text-white">
                            {formatPercent(
                                summary.f1,
                            )}
                        </p>

                        <p className="mt-2 text-xs text-zinc-600">
                            Precision / recall harmonic mean
                        </p>
                    </div>
                </section>


                {/* ================================================== */}
                {/* RECONCILIATION OVERVIEW */}
                {/* ================================================== */}

                <section className="mt-4 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-6">
                    <div>
                        <h2 className="text-base font-semibold text-white">
                            Reconciliation Overview
                        </h2>

                        <p className="mt-1 text-sm text-zinc-500">
                            Canonical benchmark results separated from
                            supplemental source-level events.
                        </p>
                    </div>

                    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
                            <p className="text-xs text-zinc-600">
                                Canonical Transactions
                            </p>

                            <p className="mt-2 text-xl font-semibold text-white">
                                {summary.canonical_transactions.toLocaleString()}
                            </p>
                        </div>


                        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
                            <p className="text-xs text-zinc-600">
                                Raw Decisions
                            </p>

                            <p className="mt-2 text-xl font-semibold text-white">
                                {summary.raw_decisions.toLocaleString()}
                            </p>
                        </div>


                        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
                            <p className="text-xs text-zinc-600">
                                Resolved
                            </p>

                            <p className="mt-2 text-xl font-semibold text-emerald-300">
                                {summary.resolved.toLocaleString()}
                            </p>
                        </div>


                        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
                            <p className="text-xs text-zinc-600">
                                Exceptions
                            </p>

                            <p className="mt-2 text-xl font-semibold text-amber-300">
                                {summary.exceptions.toLocaleString()}
                            </p>
                        </div>


                        <div className="rounded-xl border border-white/[0.06] bg-black/20 p-4">
                            <p className="text-xs text-zinc-600">
                                Supplemental Events
                            </p>

                            <p className="mt-2 text-xl font-semibold text-white">
                                {summary.supplemental_events.toLocaleString()}
                            </p>
                        </div>
                    </div>
                </section>


                {/* ================================================== */}
                {/* BREAKDOWN + PERFORMANCE */}
                {/* ================================================== */}

                <section className="mt-4 grid gap-4 xl:grid-cols-2">
                    <ExceptionBreakdown
                        statusCounts={
                            exceptions.status_counts
                        }
                    />

                    <PerformancePanel
                        benchmark={
                            benchmark
                        }
                    />
                </section>


                {/* ================================================== */}
                {/* HIGH VALUE EXCEPTIONS */}
                {/* ================================================== */}

                <section className="mt-4">
                    <HighValueExceptions
                        items={
                            highValueExceptions.items
                        }
                    />
                </section>


                {/* ================================================== */}
                {/* INTEGRITY + RAZORPAY STATUS */}
                {/* ================================================== */}

                <section className="mt-4 grid gap-4 xl:grid-cols-2">
                    <IntegrityPanel
                        summary={
                            summary
                        }
                        audit={
                            audit
                        }
                    />

                    <RazorpayPanel
                        razorpay={
                            razorpay
                        }
                    />
                </section>


                {/* ================================================== */}
                {/* RAZORPAY WORKING DEMO */}
                {/* ================================================== */}

                <section className="mt-4">
                    <RazorpayDemoPanel />
                </section>


                {/* ================================================== */}
                {/* EXCEPTION EXPLORER */}
                {/* ================================================== */}

                <section className="mt-4">
                    <ExceptionExplorer
                        items={
                            exceptions.items
                        }
                        statusCounts={
                            exceptions.status_counts
                        }
                    />
                </section>


                {/* ================================================== */}
                {/* FINANCE CONTROLLER AGENT */}
                {/* ================================================== */}

                <section className="mt-4">
                    <FinanceControllerAgent />
                </section>


                {/* ================================================== */}
                {/* FOOTER */}
                {/* ================================================== */}

                <footer className="mt-6 border-t border-white/[0.06] py-5">
                    <div className="flex flex-col gap-2 text-[11px] text-zinc-700 sm:flex-row sm:items-center sm:justify-between">
                        <p>
                            ReconAI · Razorpay Buildathon · AI Finance Controller
                        </p>

                        <p>
                            Deterministic engine · immutable evidence · AI explanation
                        </p>
                    </div>
                </footer>
            </div>
        </main>
    );
}