import {
    NextResponse,
} from "next/server";


const API_URL =
    process.env.RECONAI_API_URL ??
    "http://127.0.0.1:8000";


export async function POST() {
    try {
        const response =
            await fetch(
                `${API_URL}/api/demo/razorpay/reconcile`,
                {
                    method: "POST",

                    cache: "no-store",

                    headers: {
                        Accept:
                            "application/json",
                    },

                    signal:
                        AbortSignal.timeout(
                            30_000,
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
                "[ReconAI Razorpay Demo] Non-JSON response:",
                rawBody.slice(
                    0,
                    500,
                ),
            );

            return NextResponse.json(
                {
                    detail:
                        "Razorpay demo returned a non-JSON response.",
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
                        "Razorpay demo returned malformed JSON.",
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
            "[ReconAI Razorpay Demo] Request failed:",
            error,
        );

        return NextResponse.json(
            {
                detail:
                    "Unable to execute the Razorpay reconciliation demo.",
            },
            {
                status: 502,
            },
        );
    }
}