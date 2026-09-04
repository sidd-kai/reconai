import type {
    AuditStatus,
    BenchmarkData,
    DashboardData,
    DashboardSummary,
    ExceptionResponse,
    HighValueExceptionResponse,
    RazorpayStatus,
} from "@/lib/types";


const API_URL =
    process.env.RECONAI_API_URL ??
    "http://127.0.0.1:8000";


async function fetchJson<T>(
    path: string,
): Promise<T> {
    const url = `${API_URL}${path}`;

    const startedAt = Date.now();

    console.log(
        `[ReconAI API] START ${path}`,
    );

    try {
        const response = await fetch(
            url,
            {
                cache: "no-store",

                headers: {
                    Accept: "application/json",
                    Connection: "close",
                },

                signal: AbortSignal.timeout(
                    10_000,
                ),
            },
        );

        const elapsed =
            Date.now() -
            startedAt;

        console.log(
            `[ReconAI API] ${response.status} ${path} ${elapsed}ms`,
        );

        if (!response.ok) {
            throw new Error(
                `ReconAI API returned ${response.status} for ${path}`,
            );
        }

        const payload =
            (await response.json()) as T;

        console.log(
            `[ReconAI API] DONE ${path}`,
        );

        return payload;
    } catch (error) {
        const elapsed =
            Date.now() -
            startedAt;

        console.error(
            `[ReconAI API] FAILED ${path} after ${elapsed}ms`,
            error,
        );

        throw error;
    }
}


export async function getDashboardData(): Promise<DashboardData> {
    console.log(
        "[ReconAI API] Loading dashboard",
    );

    const summary =
        await fetchJson<DashboardSummary>(
            "/api/dashboard/summary",
        );

    const benchmark =
        await fetchJson<BenchmarkData>(
            "/api/dashboard/benchmark",
        );

    const exceptions =
        await fetchJson<ExceptionResponse>(
            "/api/dashboard/exceptions",
        );

    const highValueExceptions =
        await fetchJson<HighValueExceptionResponse>(
            "/api/dashboard/high-value-exceptions?limit=8",
        );

    const audit =
        await fetchJson<AuditStatus>(
            "/api/dashboard/audit",
        );

    const razorpay =
        await fetchJson<RazorpayStatus>(
            "/api/dashboard/razorpay",
        );

    console.log(
        "[ReconAI API] Dashboard loaded successfully",
    );

    return {
        summary,
        benchmark,
        exceptions,
        highValueExceptions,
        audit,
        razorpay,
    };
}