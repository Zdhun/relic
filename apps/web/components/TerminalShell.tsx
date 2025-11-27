import React from 'react';

export default function TerminalShell({ children }: { children: React.ReactNode }) {
    return (
        <div className="min-h-screen bg-terminal-bg p-4 md:p-8 flex flex-col">
            <header className="mb-8 border-b border-terminal-border pb-4 flex justify-between items-center">
                <h1 className="text-2xl font-bold tracking-tight text-terminal-accent">
                    AuditAI <span className="text-terminal-dim text-sm font-normal">v1.0.0</span>
                </h1>
                <div className="text-xs text-terminal-dim">SECURE CONNECTION ESTABLISHED</div>
            </header>
            <main className="flex-1 flex flex-col gap-6 max-w-7xl mx-auto w-full">
                {children}
            </main>
        </div>
    );
}
