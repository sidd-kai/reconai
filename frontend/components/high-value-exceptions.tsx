"use client";

import {
    AlertTriangle,
    ChevronRight,
    Search,
} from "lucide-react";

import {
    useEffect,
    useState,
} from "react";

import {
    ExceptionDetailDrawer,
} from "@/components/exception-detail-drawer";

import type {
    ExceptionDetail,
    ExceptionItem,
} from "@/lib/types";


interface HighValueExceptionsProps {
    items: ExceptionItem[];
}


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


function statusClasses(
    status: string | null,
): string {
    switch (status) {
        case "AMOUNT_MISMATCH":
            return "border-amber-500/20 bg-amber-500/10 text-amber-300";

        case "AMBIGUOUS":
            return "border-violet-500/20 bg-violet-500/10 text-violet-300";

        case "DUPLICATE":
            return "border-rose-500/20 bg-rose-500/10 text-rose-300";

        case "SETTLEMENT_MISMATCH":
            return "border-orange-500/20 bg-orange-500/10 text-orange-300";

        case "MISSING_PAYMENT":
        case "MISSING_LEDGER":
            return "border-sky-500/20 bg-sky-500/10 text-sky-300";

        default:
            return "border-white/10 bg-white/5 text-zinc-300";
    }
}


export function HighValueExceptions({
    items,
}: HighValueExceptionsProps) {
    const [
        selectedTransactionId,
        setSelectedTransactionId,
    ] = useState<string | null>(
        null,
    );

    const [
        detail,
        setDetail,
    ] = useState<ExceptionDetail | null>(
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
    ] = useState<string | null>(
        null,
    );


    useEffect(
        () => {
            function handleKeyDown(
                event: KeyboardEvent,
            ): void {
                if (
                    event.key ===
                    "Escape"
                ) {
                    closeDrawer();
                }
            }

            window.addEventListener(
                "keydown",
                handleKeyDown,
            );

            return () => {
                window.removeEventListener(
                    "keydown",
                    handleKeyDown,
                );
            };
        },
        [],
    );


    async function investigate(
        transactionId: string | null,
    ): Promise<void> {
        if (
            !transactionId
        ) {
            return;
        }

        setSelectedTransactionId(
            transactionId,
        );

        setDetail(
            null,
        );

        setError(
            null,
        );

        setLoading(
            true,
        );

        try {
            const response =
                await fetch(
                    `/api/reconai/exceptions/${encodeURIComponent(
                        transactionId,
                    )}`,
                    {
                        cache:
                            "no-store",
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
                console.error(
                    "[ReconAI] Investigation endpoint returned non-JSON:",
                    {
                        status:
                            response.status,
                        contentType,
                        body:
                            rawBody.slice(
                                0,
                                300,
                            ),
                    },
                );

                throw new Error(
                    `Investigation endpoint returned a non-JSON response (${response.status}).`,
                );
            }

            let payload:
                | ExceptionDetail
                | {
                    detail?: string;
                };

            try {
                payload =
                    JSON.parse(
                        rawBody,
                    ) as
                    | ExceptionDetail
                    | {
                        detail?: string;
                    };
            } catch {
                throw new Error(
                    "Investigation endpoint returned malformed JSON.",
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
                        : `Unable to investigate transaction (${response.status}).`,
                );
            }

            setDetail(
                payload as ExceptionDetail,
            );
        } catch (
        caught
        ) {
            console.error(
                "[ReconAI] Investigation failed:",
                caught,
            );

            setError(
                caught instanceof Error
                    ? caught.message
                    : "Unable to investigate transaction.",
            );
        } finally {
            setLoading(
                false,
            );
        }
    }


    function closeDrawer(): void {
        setSelectedTransactionId(
            null,
        );

        setDetail(
            null,
        );

        setError(
            null,
        );

        setLoading(
            false,
        );
    }


    return (
        <>
            <section className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035]">
                <div className="flex items-center justify-between border-b border-white/10 px-6 py-5">
                    <div>
                        <h2 className="text-base font-semibold text-white">
                            High-Value Exceptions
                        </h2>

                        <p className="mt-1 text-sm text-zinc-500">
                            Click a transaction to inspect deterministic
                            financial evidence.
                        </p>
                    </div>

                    <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-2">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="border-b border-white/10 text-xs uppercase tracking-wider text-zinc-600">
                                <th className="px-6 py-4 font-medium">
                                    Transaction
                                </th>

                                <th className="px-6 py-4 font-medium">
                                    Status
                                </th>

                                <th className="px-6 py-4 font-medium">
                                    Difference
                                </th>

                                <th className="px-6 py-4 font-medium">
                                    Confidence
                                </th>

                                <th className="px-6 py-4 font-medium">
                                    Reason
                                </th>

                                <th className="px-6 py-4 font-medium">
                                    Investigate
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {items.map(
                                (
                                    item,
                                    index,
                                ) => {
                                    const transactionId =
                                        item.transaction_id;

                                    return (
                                        <tr
                                            key={
                                                transactionId ??
                                                String(
                                                    index,
                                                )
                                            }
                                            onClick={() => {
                                                void investigate(
                                                    transactionId,
                                                );
                                            }}
                                            className={`border-b border-white/[0.06] transition last:border-none ${transactionId
                                                    ? "cursor-pointer hover:bg-indigo-500/[0.04]"
                                                    : ""
                                                }`}
                                        >
                                            <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-zinc-300">
                                                {transactionId ??
                                                    "—"}
                                            </td>

                                            <td className="whitespace-nowrap px-6 py-4">
                                                <span
                                                    className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${statusClasses(
                                                        item.status,
                                                    )}`}
                                                >
                                                    {item.status ??
                                                        "UNKNOWN"}
                                                </span>
                                            </td>

                                            <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-white">
                                                {formatMoney(
                                                    item.amount_difference,
                                                )}
                                            </td>

                                            <td className="whitespace-nowrap px-6 py-4 text-sm text-zinc-400">
                                                {(
                                                    item.confidence *
                                                    100
                                                ).toFixed(
                                                    1,
                                                )}
                                                %
                                            </td>

                                            <td className="max-w-sm px-6 py-4 text-sm text-zinc-500">
                                                {item.reason ??
                                                    "No reason recorded"}
                                            </td>

                                            <td className="px-6 py-4">
                                                {transactionId ? (
                                                    <button
                                                        type="button"
                                                        onClick={(
                                                            event,
                                                        ) => {
                                                            event.stopPropagation();

                                                            void investigate(
                                                                transactionId,
                                                            );
                                                        }}
                                                        className="inline-flex items-center gap-2 rounded-lg border border-indigo-500/15 bg-indigo-500/[0.06] px-3 py-2 text-xs font-medium text-indigo-300 transition hover:border-indigo-500/30 hover:bg-indigo-500/[0.12]"
                                                    >
                                                        <Search className="h-3.5 w-3.5" />

                                                        Inspect

                                                        <ChevronRight className="h-3.5 w-3.5" />
                                                    </button>
                                                ) : (
                                                    <span className="text-xs text-zinc-700">
                                                        —
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                },
                            )}

                            {items.length ===
                                0 && (
                                    <tr>
                                        <td
                                            colSpan={6}
                                            className="px-6 py-12 text-center text-sm text-zinc-500"
                                        >
                                            No high-value exceptions found.
                                        </td>
                                    </tr>
                                )}
                        </tbody>
                    </table>
                </div>
            </section>

            <ExceptionDetailDrawer
                open={
                    selectedTransactionId !==
                    null
                }
                loading={
                    loading
                }
                detail={
                    detail
                }
                error={
                    error
                }
                onClose={
                    closeDrawer
                }
            />
        </>
    );
}