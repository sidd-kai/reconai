import type {
    Metadata,
} from "next";

import "@/app/globals.css";


export const metadata: Metadata = {
    title:
        "ReconAI | AI Finance Controller",
    description:
        "Deterministic multi-source reconciliation for Razorpay finance operations.",
};


export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}