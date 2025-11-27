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
    const res = await fetch(`${BASE_URL}/${scanId}/result`);
    if (!res.ok) throw new Error("Failed to fetch result");
    return res.json();
}
