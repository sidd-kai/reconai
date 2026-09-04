import {
    Radio,
    Webhook,
} from "lucide-react";

import type {
    RazorpayStatus,
} from "@/lib/types";


interface RazorpayPanelProps {
    razorpay: RazorpayStatus;
}


export function RazorpayPanel({
    razorpay,
}: RazorpayPanelProps) {
    const latestPayments = razorpay.payments
        .slice()
        .reverse()
        .slice(0, 4);

    return (
        <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-6">
            <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                    <h2 className="text-base font-semibold text-white">
                        Razorpay Integration
                    </h2>

                    <p className="mt-1 text-sm text-zinc-500">
                        Payment evidence and webhook ingestion.
                    </p>
                </div>

                <span className="whitespace-nowrap rounded-full border border-sky-500/20 bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-300">
                    {razorpay.mode} MODE
                </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                    <Webhook className="mb-3 h-4 w-4 text-zinc-500" />

                    <p className="text-2xl font-semibold text-white">
                        {razorpay.webhook_event_count}
                    </p>

                    <p className="mt-1 text-xs text-zinc-500">
                        webhook events
                    </p>
                </div>

                <div className="rounded-xl border border-white/[0.07] bg-black/20 p-4">
                    <Radio className="mb-3 h-4 w-4 text-zinc-500" />

                    <p className="text-2xl font-semibold text-white">
                        {razorpay.payment_evidence_count}
                    </p>

                    <p className="mt-1 text-xs text-zinc-500">
                        payment evidence
                    </p>
                </div>
            </div>

            <div className="mt-5">
                <p className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-600">
                    Latest Payments
                </p>

                <div className="space-y-2">
                    {latestPayments.map(
                        (
                            payment,
                            index,
                        ) => {
                            const status =
                                payment.status ??
                                "unknown";

                            return (
                                <div
                                    key={
                                        payment.event_id ??
                                        payment.payment_id ??
                                        String(index)
                                    }
                                    className="flex items-center justify-between gap-4 rounded-lg border border-white/[0.06] px-3 py-3"
                                >
                                    <div className="min-w-0">
                                        <p className="truncate font-mono text-xs text-zinc-300">
                                            {payment.payment_id ??
                                                "Unknown payment"}
                                        </p>

                                        <p className="mt-1 truncate font-mono text-xs text-zinc-600">
                                            {payment.transaction_id ??
                                                "No transaction ID"}
                                        </p>
                                    </div>

                                    <span className="shrink-0 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-medium uppercase text-emerald-400">
                                        {status}
                                    </span>
                                </div>
                            );
                        },
                    )}

                    {latestPayments.length ===
                        0 && (
                            <div className="rounded-lg border border-dashed border-white/10 px-4 py-8 text-center text-xs text-zinc-600">
                                No persisted Razorpay payment evidence yet.
                            </div>
                        )}
                </div>
            </div>
        </section>
    );
}