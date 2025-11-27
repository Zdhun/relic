import React, { useEffect, useRef } from 'react';
import { ScanLog } from '@/lib/types';
import { cn } from '@/lib/utils';

export default function LogConsole({ logs }: { logs: ScanLog[] }) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="bg-black border border-terminal-border rounded-lg p-4 h-[400px] overflow-y-auto font-mono text-sm shadow-inner shadow-black/50">
            <div className="flex flex-col gap-1">
                {logs.length === 0 && (
                    <div className="text-terminal-dim italic">Waiting for scan start...</div>
                )}
                {logs.map((log, i) => (
                    <div key={i} className="flex gap-3">
                        <span className="text-terminal-dim shrink-0">[{log.ts}]</span>
                        <span className={cn(
                            "font-bold shrink-0 w-16",
                            log.level === 'INFO' && "text-blue-400",
                            log.level === 'WARNING' && "text-yellow-400",
                            log.level === 'ERROR' && "text-red-500",
                        )}>{log.level}</span>
                        <span className="text-terminal-text break-all">{log.msg}</span>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>
        </div>
    );
}
