import { ScanResult } from "./types";

const BASE_URL = "/api/scan";

export async function startScan(target: string): Promise<{ scan_id: string }> {
    const res = await fetch(`${BASE_URL}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target }),
    });
    if (!res.ok) throw new Error("Failed to start scan");
    return res.json();
}

export async function getResult(scanId: string): Promise<ScanResult> {
    const res = await fetch(`${BASE_URL}/${scanId}`);
    if (!res.ok) throw new Error("Failed to fetch result");
    return res.json();
}

export async function getAiDebug(scanId: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/${scanId}/ai-debug`);
    if (!res.ok) throw new Error("Failed to fetch AI debug info");
    return res.json();
}

export async function getAiProviderStatus(): Promise<any> {
    // Note: This endpoint is under /api/ai/providers/status, not /api/scan/...
    // We need to adjust the base URL or use absolute path if BASE_URL is specific to scans
    // Assuming BASE_URL is http://localhost:3000/api/scan, we need to go up.
    // Actually, let's just use the relative path /api/ai/providers/status which will be proxied.
    const res = await fetch(`/api/ai/providers/status`);
    if (!res.ok) throw new Error("Failed to fetch AI provider status");
    return res.json();
}

export async function generateAiAnalysis(scanId: string, provider?: string): Promise<any> {
    const url = new URL(`${BASE_URL}/${scanId}/ai-analysis`, window.location.origin);
    if (provider) {
        url.searchParams.append("provider", provider);
    }

    const res = await fetch(url.toString(), {
        method: "POST",
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to generate AI analysis");
    }
    return res.json();
}
