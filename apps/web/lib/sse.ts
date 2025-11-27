import { useEffect, useState } from "react";
import { ScanLog } from "./types";

export function useScanLogs(scanId: string | null) {
    const [logs, setLogs] = useState<ScanLog[]>([]);
    const [status, setStatus] = useState<string>("idle");

    useEffect(() => {
        if (!scanId) return;

        setLogs([]);
        setStatus("running");

        const eventSource = new EventSource(`/api/scan/${scanId}/events`);

        eventSource.onmessage = (event) => {
            // Keep alive or generic messages
        };

        eventSource.addEventListener("log", (e) => {
            const log: ScanLog = JSON.parse(e.data);
            setLogs((prev) => [...prev, log]);
        });

        eventSource.addEventListener("done", (e) => {
            const data = JSON.parse(e.data);
            setStatus(data.status);
            eventSource.close();
        });

        eventSource.onerror = () => {
            eventSource.close();
            setStatus("error");
        };

        return () => {
            eventSource.close();
        };
    }, [scanId]);

    return { logs, status };
}
