"use client";

import React, { useState } from 'react';
import TerminalShell from '@/components/TerminalShell';
import LogConsole from '@/components/LogConsole';
import ResultTabs from '@/components/ResultTabs';
import { useScanLogs } from '@/lib/sse';
import { startScan, getResult } from '@/lib/api';
import { ScanResult } from '@/lib/types';
import { Shield, Play, Loader2 } from 'lucide-react';

export default function Page() {
    const [target, setTarget] = useState('');
    const [scanId, setScanId] = useState<string | null>(null);
    const [result, setResult] = useState<ScanResult | null>(null);

    const { logs, status } = useScanLogs(scanId);

    // Poll for result when done
    React.useEffect(() => {
        if (status === 'done' && scanId && !result) {
            getResult(scanId).then(setResult);
        }
    }, [status, scanId, result]);

    const handleStart = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!target) return;

        setResult(null);
        try {
            const { scan_id } = await startScan(target);
            setScanId(scan_id);
        } catch (err) {
            alert("Failed to start scan");
        }
    };

    return (
        <TerminalShell>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
                <div className="flex flex-col gap-6">
                    <div className="bg-terminal-dim/10 p-6 rounded-lg border border-terminal-border">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Shield className="text-terminal-accent" size={20} />
                            New Security Scan
                        </h2>
                        <form onSubmit={handleStart} className="flex gap-4">
                            <input
                                type="text"
                                placeholder="Enter target (e.g., localhost)"
                                className="flex-1 bg-black border border-terminal-border rounded px-4 py-2 focus:outline-none focus:border-terminal-accent text-white placeholder:text-terminal-dim"
                                value={target}
                                onChange={(e) => setTarget(e.target.value)}
                                disabled={status === 'running'}
                            />
                            <button
                                type="submit"
                                disabled={status === 'running' || !target}
                                className="bg-terminal-accent text-black font-bold px-6 py-2 rounded hover:bg-terminal-accent/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {status === 'running' ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
                                SCAN
                            </button>
                        </form>
                    </div>

                    <div className="flex-1 flex flex-col">
                        <h3 className="text-sm text-terminal-dim mb-2 uppercase tracking-wider">Live Operation Logs</h3>
                        <LogConsole logs={logs} />
                    </div>
                </div>

                <div className="bg-terminal-dim/5 rounded-lg border border-terminal-border p-6 min-h-[500px]">
                    {result ? (
                        <ResultTabs result={result} />
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-terminal-dim gap-4">
                            <Shield size={48} className="opacity-20" />
                            <p>Ready to audit. Enter a target to begin.</p>
                        </div>
                    )}
                </div>
            </div>
        </TerminalShell>
    );
}
