import {
    Activity,
    Clock3,
    Gauge,
    Repeat2,
} from "lucide-react";

import type {
    BenchmarkData,
} from "@/lib/types";


interface PerformancePanelProps {
    benchmark: BenchmarkData;
}


export function PerformancePanel({
    benchmark,
}: PerformancePanelProps) {
    const items = [
        {
            label: "Median throughput",
            value: `${benchmark.median_records_per_second.toFixed(
                2,
            )} rec/s`,
            icon: Gauge,
        },
        {
            label: "Median batch latency",
            value: `${benchmark.median_latency_seconds.toFixed(
                3,
            )} sec`,
            icon: Clock3,
        },
        {
            label: "Raw decision throughput",
            value: `${benchmark.median_decisions_per_second.toFixed(
                2,
            )} /s`,
            icon: Activity,
        },
        {
            label: "Deterministic runs",
            value:
                benchmark.deterministic_across_runs
                    ? "Verified"
                    : "Failed",
            icon: Repeat2,
        },
    ];

    return (
        <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-6">
            <div className="mb-6">
                <h2 className="text-base font-semibold text-white">
                    Engine Performance
                </h2>

                <p className="mt-1 text-sm text-zinc-500">
                    Measured directly around ReconciliationEngine.reconcile().
                </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
                {items.map(
                    ({
                        label,
                        value,
                        icon: Icon,
                    }) => (
                        <div
                            key={label}
                            className="rounded-xl border border-white/[0.07] bg-black/20 p-4"
                        >
                            <div className="mb-3 flex items-center gap-2 text-zinc-500">
                                <Icon className="h-4 w-4" />

                                <span className="text-xs">
                                    {label}
                                </span>
                            </div>

                            <div className="text-lg font-semibold text-white">
                                {value}
                            </div>
                        </div>
                    ),
                )}
            </div>

            <div className="mt-5 border-t border-white/10 pt-4">
                <p className="text-xs leading-5 text-zinc-600">
                    Benchmark excludes source loading and includes deterministic
                    reconciliation, immutable audit writes and exception-manifest
                    writes.
                </p>
            </div>
        </section>
    );
}