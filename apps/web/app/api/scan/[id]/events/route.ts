import { NextRequest, NextResponse } from 'next/server';

const SCANNER_URL = process.env.SCANNER_BASE_URL || 'http://localhost:8000';

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
    const id = params.id;

    // Proxy SSE
    const response = await fetch(`${SCANNER_URL}/scan/${id}/events`, {
        headers: {
            'Accept': 'text/event-stream',
        }
    });

    if (!response.ok || !response.body) {
        return NextResponse.json({ error: 'Failed to connect to scanner' }, { status: 500 });
    }

    // Pass the stream through
    return new NextResponse(response.body, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        },
    });
}
