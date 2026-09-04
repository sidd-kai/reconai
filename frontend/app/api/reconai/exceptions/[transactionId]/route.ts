import {
    NextResponse,
} from "next/server";


const API_URL =
    process.env.RECONAI_API_URL ??
    "http://127.0.0.1:8000";


interface RouteContext {
    params: Promise<{
        transactionId: string;
    }>;
}


export async function GET(
    _request: Request,
    context: RouteContext,
) {
    const {
        transactionId,
    } = await context.params;

    const encodedTransactionId =
        encodeURIComponent(
            transactionId,
        );

    const url =
        `${API_URL}/api/dashboard/exceptions/${encodedTransactionId}`;

    try {
        console.log(
            `[ReconAI Proxy] GET ${url}`,
        );

        const response =
            await fetch(
                url,
                {
                    cache: "no-store",

                    headers: {
                        Accept: "application/json",
                    },

                    signal:
                        AbortSignal.timeout(
                            10_000,
                        ),
                },
            );

        const contentType =
            response.headers.get(
                "content-type",
            ) ?? "";

        const rawBody =
            await response.text();

        console.log(
            `[ReconAI Proxy] ${response.status} ${contentType}`,
        );

        if (
            !contentType.includes(
                "application/json",
            )
        ) {
            console.error(
                "[ReconAI Proxy] Non-JSON response:",
                rawBody.slice(
                    0,
                    300,
                ),
            );

            return NextResponse.json(
                {
                    detail:
                        "FastAPI returned a non-JSON response.",
                    upstream_status:
                        response.status,
                },
                {
                    status: 502,
                },
            );
        }

        let payload: unknown;

        try {
            payload =
                JSON.parse(
                    rawBody,
                );
        } catch {
            return NextResponse.json(
                {
                    detail:
                        "FastAPI returned malformed JSON.",
                },
                {
                    status: 502,
                },
            );
        }

        return NextResponse.json(
            payload,
            {
                status:
                    response.status,
            },
        );
    } catch (error) {
        console.error(
            "[ReconAI Proxy] Exception detail proxy failed",
            error,
        );

        return NextResponse.json(
            {
                detail:
                    "Unable to retrieve deterministic exception evidence.",
            },
            {
                status: 502,
            },
        );
    }
}