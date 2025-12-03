import { useState, useRef } from 'react';
import { generateAiAnalysis } from '../lib/api';

interface AiAnalysisSectionProps {
    scanId: string;
    provider: string;
}

export default function AiAnalysisSection({ scanId, provider }: AiAnalysisSectionProps) {
    const [analysis, setAnalysis] = useState<any | null>(null);
    const [loading, setLoading] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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

    const [streamedText, setStreamedText] = useState("");
    const isGeneratingRef = useRef(false);

    const handleGenerate = async () => {
        if (isGeneratingRef.current) return;
        isGeneratingRef.current = true;

        setLoading(true);
        setError(null);
        setStreamedText("");
        setAnalysis(null);

        try {
            const result = await generateAiAnalysis(scanId, provider, (chunk) => {
                setStreamedText(prev => prev + chunk);
            });
            setAnalysis(result);
            // Auto-download PDF on success
            await handleDownloadPdf();
        } catch (err: any) {
            setError(err.message || "Failed to generate analysis");
        } finally {
            setLoading(false);
            isGeneratingRef.current = false;
        }
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
                    <p className="font-bold">Error: {error}</p>
                    {(error.includes("Ollama") || error.includes("OpenRouter") || error.includes("connect") || error.includes("API key")) && (
                        <div className="mt-2 text-sm text-red-300 opacity-80">
                            <p className="font-semibold mb-1">Troubleshooting:</p>
                            <ul className="list-disc list-inside ml-2 space-y-1">
                                <li>If using <strong>Ollama</strong>, ensure it is running locally (e.g., <code>ollama serve</code>).</li>
                                <li>If using <strong>OpenRouter</strong>, check that <code>OPENROUTER_API_KEY</code> is set in your <code>.env</code> file.</li>
                            </ul>
                        </div>
                    )}
                </div>
            )}

            {(analysis || streamedText) && (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="bg-terminal-dim/5 border border-terminal-border p-4 rounded overflow-x-auto">
                        <h4 className="text-sm uppercase tracking-wider text-terminal-dim mb-2">
                            {analysis ? "Raw Analysis Result" : "Generating Analysis..."}
                        </h4>
                        <pre className="text-xs text-terminal-text font-mono whitespace-pre-wrap">
                            {analysis ? JSON.stringify(analysis, null, 2) : streamedText}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}
