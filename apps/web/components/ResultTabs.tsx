import React, { useState, useEffect } from 'react';
import { ScanResult } from '@/lib/types';
import { Download, Bot, Code } from 'lucide-react';
import { getAiDebug } from '@/lib/api';
import AiProviderToggle from './AiProviderToggle';
import AiAnalysisSection from './AiAnalysisSection';

export default function ResultTabs({ result }: { result: ScanResult | null }) {
    const [showAiDebug, setShowAiDebug] = useState(false);
    const [aiView, setAiView] = useState<any>(null);
    const [loadingAi, setLoadingAi] = useState(false);
    const [selectedProvider, setSelectedProvider] = useState('ollama');

    useEffect(() => {
        if (showAiDebug && !aiView && result?.scan_id) {
            setLoadingAi(true);
            getAiDebug(result.scan_id)
                .then(data => setAiView(data.ai_view))
                .catch(err => console.error("Failed to load AI view", err))
                .finally(() => setLoadingAi(false));
        }
    }, [showAiDebug, result?.scan_id, aiView]);

    if (!result) return null;

    return (
        <div className="flex flex-col gap-6">
            <AiProviderToggle selectedProvider={selectedProvider} onSelect={setSelectedProvider} />

            {result.scan_status === 'blocked' && (
                <div className="bg-red-500/10 border border-red-500/50 p-4 rounded text-red-200">
                    <div className="font-bold flex items-center gap-2">
                        <span>🛡️ Scan status: BLOCKED BY WAF</span>
                    </div>
                    <p className="text-sm mt-1 opacity-90">
                        The scanner was blocked by a security mechanism ({result.blocking_mechanism || 'WAF'}).
                        Only limited information is available. Results below may not reflect the actual security posture of the application.
                    </p>
                </div>
            )}

            <div className="flex justify-between items-center bg-terminal-dim/10 p-4 rounded border border-terminal-border">
                <div>
                    <div className="text-sm text-terminal-dim">Target</div>
                    <div className="text-xl font-bold">{result.target}</div>
                </div>
                <div className="text-right">
                    <div className="text-sm text-terminal-dim">Grade</div>
                    <div className={`text-4xl font-bold ${result.grade === 'A' ? 'text-green-500' :
                        result.grade === 'B' ? 'text-blue-500' :
                            result.grade === 'C' ? 'text-yellow-500' :
                                result.grade === 'N/A' ? 'text-gray-500' : 'text-red-500'
                        }`}>{result.grade}</div>
                </div>
            </div>

            <div className="space-y-4">
                <h3 className="text-lg font-semibold text-terminal-accent border-b border-terminal-border pb-2">Top Findings</h3>
                {result.findings.map((finding, i) => (
                    <div key={i} className="bg-terminal-dim/5 border border-terminal-border p-4 rounded hover:border-terminal-accent/50 transition-colors">
                        <div className="flex justify-between mb-2">
                            <span className="font-bold text-white">{finding.title}</span>
                            <span className={`text-xs px-2 py-0.5 rounded border ${finding.severity === 'High' ? 'border-red-500 text-red-500' :
                                finding.severity === 'Medium' ? 'border-yellow-500 text-yellow-500' :
                                    'border-blue-500 text-blue-500'
                                }`}>{finding.severity}</span>
                        </div>
                        <p className="text-sm text-terminal-dim mb-2">{finding.impact}</p>
                        <p className="text-xs text-terminal-accent">Rec: {finding.recommendation}</p>
                    </div>
                ))}
            </div>

            <AiAnalysisSection scanId={result.scan_id} provider={selectedProvider} />


            {result.debug_info && (
                <div className="space-y-4 pt-6 border-t border-terminal-border">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-terminal-accent">Debug Info</h3>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setShowAiDebug(false)}
                                className={`px-3 py-1 rounded text-xs font-bold flex items-center gap-2 ${!showAiDebug ? 'bg-terminal-accent text-black' : 'bg-terminal-dim/20 text-terminal-dim hover:bg-terminal-dim/30'}`}
                            >
                                <Code size={14} /> Raw JSON
                            </button>
                            <button
                                onClick={() => setShowAiDebug(true)}
                                className={`px-3 py-1 rounded text-xs font-bold flex items-center gap-2 ${showAiDebug ? 'bg-terminal-accent text-black' : 'bg-terminal-dim/20 text-terminal-dim hover:bg-terminal-dim/30'}`}
                            >
                                <Bot size={14} /> AI View
                            </button>
                        </div>
                    </div>

                    <div className="bg-terminal-dim/5 border border-terminal-border p-4 rounded overflow-x-auto relative">
                        {showAiDebug && loadingAi && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                                <span className="text-terminal-accent animate-pulse">Loading AI View...</span>
                            </div>
                        )}
                        <pre className="text-xs text-terminal-dim font-mono">
                            {showAiDebug
                                ? JSON.stringify(aiView || {}, null, 2)
                                : JSON.stringify(result.debug_info, null, 2)
                            }
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}
