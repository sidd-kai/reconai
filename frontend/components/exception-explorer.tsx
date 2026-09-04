"use client";

import {
    ChevronLeft,
    ChevronRight,
    Filter,
    Search,
    SlidersHorizontal,
} from "lucide-react";

import {
    useMemo,
    useState,
} from "react";

import {
    ExceptionDetailDrawer,
} from "@/components/exception-detail-drawer";

import type {
    ExceptionDetail,
    ExceptionItem,
} from "@/lib/types";


interface ExceptionExplorerProps {
    items: ExceptionItem[];
    statusCounts: Record<
        string,
        number
    >;
}


const PAGE_SIZE = 10;


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
            return "border-sky-500/20 bg-sky-500/10 text-sky-300";

        case "MISSING_LEDGER":
            return "border-cyan-500/20 bg-cyan-500/10 text-cyan-300";

        case "UNRESOLVED":
            return "border-zinc-500/20 bg-zinc-500/10 text-zinc-300";

        default:
            return "border-white/10 bg-white/5 text-zinc-300";
    }
}


export function ExceptionExplorer({
    items,
    statusCounts,
}: ExceptionExplorerProps) {
    const [
        searchQuery,
        setSearchQuery,
    ] = useState(
        "",
    );

    const [
        selectedStatus,
        setSelectedStatus,
    ] = useState(
        "ALL",
    );

    const [
        page,
        setPage,
    ] = useState(
        1,
    );

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


    const statuses = useMemo(
        () => [
            "ALL",
            ...Object.keys(
                statusCounts,
            ).sort(),
        ],
        [
            statusCounts,
        ],
    );


    const filteredItems = useMemo(
        () => {
            const normalizedSearch =
                searchQuery
                    .trim()
                    .toLowerCase();

            return items.filter(
                (item) => {
                    const status =
                        item.status ??
                        "UNKNOWN";

                    if (
                        selectedStatus !==
                        "ALL" &&
                        status !==
                        selectedStatus
                    ) {
                        return false;
                    }

                    if (
                        !normalizedSearch
                    ) {
                        return true;
                    }

                    const searchable =
                        [
                            item.transaction_id,
                            item.status,
                            item.reason,
                            item.method,
                            item.evidence.payment_id,
                            item.evidence.ledger_id,
                            item.evidence.settlement_id,
                        ]
                            .filter(
                                Boolean,
                            )
                            .join(
                                " ",
                            )
                            .toLowerCase();

                    return searchable.includes(
                        normalizedSearch,
                    );
                },
            );
        },
        [
            items,
            searchQuery,
            selectedStatus,
        ],
    );


    const totalPages =
        Math.max(
            1,
            Math.ceil(
                filteredItems.length /
                PAGE_SIZE,
            ),
        );


    const safePage =
        Math.min(
            page,
            totalPages,
        );


    const pageItems =
        filteredItems.slice(
            (
                safePage -
                1
            ) *
            PAGE_SIZE,
            safePage *
            PAGE_SIZE,
        );


    function chooseStatus(
        status: string,
    ): void {
        setSelectedStatus(
            status,
        );

        setPage(
            1,
        );
    }


    function updateSearch(
        value: string,
    ): void {
        setSearchQuery(
            value,
        );

        setPage(
            1,
        );
    }


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
                throw new Error(
                    `Investigation endpoint returned non-JSON (${response.status}).`,
                );
            }

            const payload =
                JSON.parse(
                    rawBody,
                ) as
                | ExceptionDetail
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
                        : "Unable to investigate transaction.",
                );
            }

            setDetail(
                payload as ExceptionDetail,
            );
        } catch (
        caught
        ) {
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
                <div className="border-b border-white/10 px-6 py-5">
                    <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                        <div>
                            <div className="flex items-center gap-2">
                                <SlidersHorizontal className="h-4 w-4 text-indigo-400" />

                                <h2 className="text-base font-semibold text-white">
                                    Exception Explorer
                                </h2>
                            </div>

                            <p className="mt-2 text-sm text-zinc-500">
                                Search and investigate all current canonical finance
                                exceptions.
                            </p>
                        </div>

                        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-2 text-xs text-zinc-400">
                            <Filter className="h-3.5 w-3.5" />

                            {filteredItems.length.toLocaleString()} visible of{" "}
                            {items.length.toLocaleString()}
                        </div>
                    </div>

                    <div className="mt-5 relative">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />

                        <input
                            type="search"
                            value={searchQuery}
                            onChange={(
                                event,
                            ) => {
                                updateSearch(
                                    event.target.value,
                                );
                            }}
                            placeholder="Search transaction, payment, ledger, settlement, status or reason..."
                            className="w-full rounded-xl border border-white/10 bg-black/30 py-3 pl-10 pr-4 text-sm text-white outline-none transition placeholder:text-zinc-700 focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/10"
                        />
                    </div>

                    <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
                        {statuses.map(
                            (status) => {
                                const active =
                                    selectedStatus ===
                                    status;

                                const count =
                                    status ===
                                        "ALL"
                                        ? items.length
                                        : statusCounts[
                                        status
                                        ] ??
                                        0;

                                return (
                                    <button
                                        key={status}
                                        type="button"
                                        onClick={() => {
                                            chooseStatus(
                                                status,
                                            );
                                        }}
                                        className={`whitespace-nowrap rounded-full border px-3 py-2 text-xs transition ${active
                                                ? "border-indigo-400/40 bg-indigo-500/15 text-indigo-200"
                                                : "border-white/10 bg-white/[0.025] text-zinc-500 hover:border-white/20 hover:text-zinc-300"
                                            }`}
                                    >
                                        {status.replaceAll(
                                            "_",
                                            " ",
                                        )}

                                        <span className="ml-2 opacity-60">
                                            {count}
                                        </span>
                                    </button>
                                );
                            },
                        )}
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
                                    Action
                                </th>
                            </tr>
                        </thead>

                        <tbody>
                            {pageItems.map(
                                (
                                    item,
                                    index,
                                ) => (
                                    <tr
                                        key={
                                            item.transaction_id ??
                                            index
                                        }
                                        onClick={() => {
                                            void investigate(
                                                item.transaction_id,
                                            );
                                        }}
                                        className="cursor-pointer border-b border-white/[0.06] transition last:border-none hover:bg-indigo-500/[0.04]"
                                    >
                                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-zinc-300">
                                            {item.transaction_id ??
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

                                        <td className="max-w-md px-6 py-4 text-sm text-zinc-500">
                                            {item.reason ??
                                                "No reason recorded"}
                                        </td>

                                        <td className="px-6 py-4">
                                            <button
                                                type="button"
                                                onClick={(
                                                    event,
                                                ) => {
                                                    event.stopPropagation();

                                                    void investigate(
                                                        item.transaction_id,
                                                    );
                                                }}
                                                className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-zinc-300 transition hover:border-indigo-500/30 hover:bg-indigo-500/10 hover:text-indigo-300"
                                            >
                                                Inspect

                                                <ChevronRight className="h-3.5 w-3.5" />
                                            </button>
                                        </td>
                                    </tr>
                                ),
                            )}

                            {pageItems.length ===
                                0 && (
                                    <tr>
                                        <td
                                            colSpan={6}
                                            className="px-6 py-16 text-center"
                                        >
                                            <Search className="mx-auto h-5 w-5 text-zinc-700" />

                                            <p className="mt-3 text-sm text-zinc-500">
                                                No exceptions match the current filters.
                                            </p>
                                        </td>
                                    </tr>
                                )}
                        </tbody>
                    </table>
                </div>

                <div className="flex flex-col gap-3 border-t border-white/10 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs text-zinc-600">
                        Page {safePage} of {totalPages}
                    </p>

                    <div className="flex gap-2">
                        <button
                            type="button"
                            disabled={
                                safePage <=
                                1
                            }
                            onClick={() => {
                                setPage(
                                    (
                                        current,
                                    ) =>
                                        Math.max(
                                            1,
                                            current -
                                            1,
                                        ),
                                );
                            }}
                            className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 transition hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-30"
                        >
                            <ChevronLeft className="h-3.5 w-3.5" />

                            Previous
                        </button>

                        <button
                            type="button"
                            disabled={
                                safePage >=
                                totalPages
                            }
                            onClick={() => {
                                setPage(
                                    (
                                        current,
                                    ) =>
                                        Math.min(
                                            totalPages,
                                            current +
                                            1,
                                        ),
                                );
                            }}
                            className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 transition hover:bg-white/[0.05] disabled:cursor-not-allowed disabled:opacity-30"
                        >
                            Next

                            <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                    </div>
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