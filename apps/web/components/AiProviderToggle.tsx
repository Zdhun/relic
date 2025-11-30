import { useEffect, useState } from 'react';
import { getAiProviderStatus } from '../lib/api';

interface ProviderStatus {
    available: boolean;
    model?: string;
    configured?: boolean;
}

interface AiProviderToggleProps {
    selectedProvider: string;
    onSelect: (provider: string) => void;
}

export default function AiProviderToggle({ selectedProvider, onSelect }: AiProviderToggleProps) {
    const [status, setStatus] = useState<Record<string, ProviderStatus>>({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getAiProviderStatus()
            .then(setStatus)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    const getStatusColor = (provider: string) => {
        if (loading) return "bg-terminal-dim";
        return status[provider]?.available ? "bg-green-500" : "bg-red-500";
    };

    const getStatusText = (provider: string) => {
        if (loading) return "Checking...";
        return status[provider]?.available ? "Connected" : "Unavailable";
    };

    return (
        <div className="flex flex-col items-center gap-2 mb-6">
            <div className="flex bg-terminal-dim/10 p-1 rounded-lg border border-terminal-border">
                {['ollama', 'openrouter'].map((provider) => (
                    <button
                        key={provider}
                        onClick={() => onSelect(provider)}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${selectedProvider === provider
                                ? 'bg-terminal-accent text-black shadow-lg shadow-terminal-accent/20'
                                : 'text-terminal-dim hover:text-terminal-text'
                            }`}
                    >
                        {provider === 'ollama' ? 'Ollama (Local)' : 'OpenRouter (Cloud)'}
                    </button>
                ))}
            </div>

            <div className="flex gap-4 text-xs text-terminal-dim">
                {['ollama', 'openrouter'].map((provider) => (
                    <div key={provider} className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${getStatusColor(provider)}`} />
                        <span className="capitalize">{provider}: {getStatusText(provider)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
