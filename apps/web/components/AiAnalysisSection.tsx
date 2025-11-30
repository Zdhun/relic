import { useState } from 'react';
import { generateAiAnalysis } from '../lib/api';

interface Vulnerability {
    title: string;
    severity: string;
    area: string;
    explanation_simple: string;
    fix_recommendation: string;
}

interface SiteMap {
    total_pages: number;
    pages: string[];
}

interface GlobalScore {
    letter: string;
    numeric: number;
}

interface AnalysisResult {
    global_score: GlobalScore;
    overall_risk_level: string;
    executive_summary: string;
    top_3_vulnerabilities: Vulnerability[];
    site_map: SiteMap;
}

interface AiAnalysisSectionProps {
    scanId: string;
    provider: string;
}

export default function AiAnalysisSection({ scanId, provider }: AiAnalysisSectionProps) {
    const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showDebug, setShowDebug] = useState(false);

    const handleGenerate = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await generateAiAnalysis(scanId, provider);
            setAnalysis(result);
        } catch (err: any) {
            setError(err.message || "Failed to generate analysis");
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadPdf = async () => {
        setIsDownloading(true);
        try {
            // Use the same provider as selected
            const url = new URL(`/api/scan/${scanId}/ai-report.pdf`, window.location.origin);
            if (provider) {
                url.searchParams.append("provider", provider);
            }

            const res = await fetch(url.toString());
            if (!res.ok) throw new Error("Failed to download PDF");

            const blob = await res.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = `ai_report_${scanId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(blobUrl);
            document.body.removeChild(a);
        } catch (e) {
            console.error(e);
            alert("Failed to download PDF report. Please try again.");
        } finally {
            setIsDownloading(false);
        }
    };

    const getRiskColor = (risk: string) => {
        const r = risk.toLowerCase();
        if (r.includes('critique') || r.includes('critical')) return 'text-red-500 border-red-500 bg-red-500/10';
        if (r.includes('élevé') || r.includes('high')) return 'text-orange-500 border-orange-500 bg-orange-500/10';
        if (r.includes('moyen') || r.includes('medium')) return 'text-yellow-500 border-yellow-500 bg-yellow-500/10';
        return 'text-green-500 border-green-500 bg-green-500/10';
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold text-terminal-accent">AI Security Analysis</h3>
                <div className="flex gap-3">
                    {analysis && (
                        <button
                            onClick={handleDownloadPdf}
                            disabled={isDownloading}
                            className="px-4 py-2 bg-terminal-dim/20 text-terminal-accent border border-terminal-accent/50 font-bold rounded hover:bg-terminal-accent/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isDownloading ? "Downloading..." : "Download PDF Report"}
                        </button>
                    )}
                    <button
                        onClick={handleGenerate}
                        disabled={loading}
                        className="px-4 py-2 bg-terminal-accent text-black font-bold rounded hover:bg-terminal-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading ? "Generating..." : "Generate Analysis"}
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-4 border border-red-500/50 bg-red-500/10 text-red-400 rounded">
                    Error: {error}
                </div>
            )}

            {analysis && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

                    {/* Debug Toggle */}
                    <div className="flex justify-end">
                        <button
                            onClick={() => setShowDebug(!showDebug)}
                            className="text-xs text-terminal-dim hover:text-terminal-accent transition-colors"
                        >
                            {showDebug ? "Hide Raw Response" : "Show Raw Response"}
                        </button>
                    </div>

                    {/* Raw Response Debug View */}
                    {showDebug && (
                        <div className="bg-terminal-dim/5 border border-terminal-border p-4 rounded overflow-x-auto">
                            <pre className="text-xs text-terminal-dim font-mono">
                                {JSON.stringify(analysis, null, 2)}
                            </pre>
                        </div>
                    )}

                    {/* Global Score & Executive Summary */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="p-6 border rounded-lg flex flex-col items-center justify-center text-center bg-terminal-dim/5 border-terminal-border">
                            <h4 className="text-sm uppercase tracking-wider opacity-80 mb-2 text-terminal-dim">Global Score</h4>
                            <div className="flex items-baseline gap-2">
                                <span className={`text-5xl font-bold ${analysis.global_score.letter === 'A' ? 'text-green-500' :
                                    analysis.global_score.letter === 'B' ? 'text-blue-500' :
                                        analysis.global_score.letter === 'C' ? 'text-yellow-500' :
                                            'text-red-500'
                                    }`}>{analysis.global_score.letter}</span>
                                <span className="text-xl text-terminal-dim">/ {analysis.global_score.numeric}</span>
                            </div>
                            <div className={`mt-2 px-3 py-1 rounded-full text-xs border ${getRiskColor(analysis.overall_risk_level)}`}>
                                {analysis.overall_risk_level}
                            </div>
                        </div>
                        <div className="md:col-span-2 p-6 bg-terminal-dim/5 border border-terminal-border rounded-lg">
                            <h4 className="text-sm uppercase tracking-wider text-terminal-dim mb-3">Executive Summary</h4>
                            <p className="text-terminal-text leading-relaxed">{analysis.executive_summary}</p>
                        </div>
                    </div>

                    {/* Top 3 Vulnerabilities */}
                    <div>
                        <h4 className="text-sm uppercase tracking-wider text-terminal-dim mb-4">Top 3 Critical Vulnerabilities</h4>
                        <div className="grid gap-4">
                            {analysis.top_3_vulnerabilities.map((vuln, i) => (
                                <div key={i} className="p-4 border border-terminal-border rounded-lg bg-terminal-dim/5 hover:border-terminal-accent/50 transition-colors">
                                    <div className="flex justify-between items-start mb-2">
                                        <h5 className="font-bold text-terminal-accent">{vuln.title}</h5>
                                        <span className={`text-xs px-2 py-1 rounded border ${getRiskColor(vuln.severity)}`}>
                                            {vuln.severity}
                                        </span>
                                    </div>
                                    <div className="text-sm text-terminal-dim mb-2">Area: {vuln.area}</div>
                                    <p className="text-sm text-terminal-text mb-3">{vuln.explanation_simple}</p>
                                    <div className="text-sm bg-terminal-dim/10 p-3 rounded border border-terminal-border/50">
                                        <span className="font-bold text-terminal-accent">Fix: </span>
                                        {vuln.fix_recommendation}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Site Map */}
                    <div className="p-6 bg-terminal-dim/5 border border-terminal-border rounded-lg">
                        <div className="flex justify-between items-center mb-4">
                            <h4 className="text-sm uppercase tracking-wider text-terminal-dim">Site Map</h4>
                            <span className="text-xs text-terminal-accent border border-terminal-accent/30 px-2 py-1 rounded">
                                {analysis.site_map.total_pages} Pages Found
                            </span>
                        </div>
                        <div className="max-h-40 overflow-y-auto space-y-1">
                            {analysis.site_map.pages.map((page, i) => (
                                <div key={i} className="text-sm text-terminal-dim font-mono truncate hover:text-terminal-text transition-colors">
                                    {page}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
