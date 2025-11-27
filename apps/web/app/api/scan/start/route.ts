import { NextResponse } from 'next/server';

const SCANNER_URL = process.env.SCANNER_BASE_URL || 'http://localhost:8000';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const res = await fetch(`${SCANNER_URL}/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            const error = await res.json();
            return NextResponse.json(error, { status: res.status });
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }
}
