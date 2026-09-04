import type {
    ReactNode,
} from "react";


interface MetricCardProps {
    title: string;

    value: string;

    subtitle: string;

    icon: ReactNode;
}


export function MetricCard({
    title,
    value,
    subtitle,
    icon,
}: MetricCardProps) {
    return (
        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5">
            <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                    <p className="text-xs uppercase tracking-wider text-zinc-600">
                        {title}
                    </p>

                    <p className="mt-3 text-2xl font-semibold tracking-tight text-white">
                        {value}
                    </p>

                    <p className="mt-2 text-xs leading-5 text-zinc-500">
                        {subtitle}
                    </p>
                </div>

                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/[0.07] bg-white/[0.03] text-zinc-400">
                    {icon}
                </div>
            </div>
        </div>
    );
}