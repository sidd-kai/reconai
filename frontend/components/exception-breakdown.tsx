"use client";

import {
    Bar,
    BarChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";


interface ExceptionBreakdownProps {
    statusCounts: Record<string, number>;
}


export function ExceptionBreakdown({
    statusCounts,
}: ExceptionBreakdownProps) {
    const data = Object.entries(
        statusCounts,
    )
        .map(
            ([status, count]) => ({
                status,
                count,
            }),
        )
        .sort(
            (a, b) =>
                b.count - a.count,
        );

    return (
        <section className="rounded-2xl border border-white/10 bg-white/[0.035] p-6">
            <div className="mb-6">
                <h2 className="text-base font-semibold text-white">
                    Exception Breakdown
                </h2>

                <p className="mt-1 text-sm text-zinc-500">
                    Current finance exceptions by deterministic engine status.
                </p>
            </div>

            {data.length === 0 ? (
                <div className="flex h-72 items-center justify-center text-sm text-zinc-500">
                    No current exception data.
                </div>
            ) : (
                <div className="h-72 w-full">
                    <ResponsiveContainer
                        width="100%"
                        height="100%"
                    >
                        <BarChart
                            data={data}
                            margin={{
                                top: 10,
                                right: 5,
                                left: -15,
                                bottom: 30,
                            }}
                        >
                            <CartesianGrid
                                strokeDasharray="3 3"
                                stroke="rgba(255,255,255,0.07)"
                                vertical={false}
                            />

                            <XAxis
                                dataKey="status"
                                tick={{
                                    fill: "#71717a",
                                    fontSize: 10,
                                }}
                                angle={-20}
                                textAnchor="end"
                                axisLine={false}
                                tickLine={false}
                            />

                            <YAxis
                                allowDecimals={false}
                                tick={{
                                    fill: "#71717a",
                                    fontSize: 11,
                                }}
                                axisLine={false}
                                tickLine={false}
                            />

                            <Tooltip
                                cursor={{
                                    fill: "rgba(255,255,255,0.03)",
                                }}
                                contentStyle={{
                                    background: "#18181b",
                                    border:
                                        "1px solid rgba(255,255,255,0.1)",
                                    borderRadius: "12px",
                                    color: "#fff",
                                }}
                            />

                            <Bar
                                dataKey="count"
                                fill="#818cf8"
                                radius={[
                                    6,
                                    6,
                                    0,
                                    0,
                                ]}
                            />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </section>
    );
}