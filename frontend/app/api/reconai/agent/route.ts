import {
    NextResponse,
} from "next/server";


const API_URL =
    process.env.RECONAI_API_URL ??
    "http://127.0.0.1:8000";


interface AgentProxyRequest {
    message?: string;

    transaction_id?: string | null;

    action?: string | null;

    limit?: number;
}


export async function POST(
    request: Request,
) {
    try {
        const body =
            (await request.json()) as AgentProxyRequest;

        const response =
            await fetch(
                `${API_URL}/api/agent/query`,
                {
                    method: "POST",

                    cache: "no-store",

                    headers: {
                        Accept:
                            "application/json",

                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify(
                        {
                            message:
                                body.message ??
                                "",

                            transaction_id:
                                body.transaction_id ??
                                null,

                            action:
                                body.action ??
                                null,

                            limit:
                                body.limit ??
                                5,
                        },
                    ),

                    signal:
                        AbortSignal.timeout(
                            180_000,
                        ),
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
                "[ReconAI Agent Proxy] Non-JSON response:",
                rawBody.slice(
                    0,
                    500,
                ),
            );

            return NextResponse.json(
                {
                    detail:
                        "ReconAI returned a non-JSON response.",
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
                        "ReconAI returned malformed JSON.",
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
            "[ReconAI Agent Proxy] Request failed:",
            error,
        );

        return NextResponse.json(
            {
                detail:
                    "Unable to reach the ReconAI finance controller.",
            },
            {
                status: 502,
            },
        );
    }
}
