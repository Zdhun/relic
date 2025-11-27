import { NextResponse } from 'next/server';

const SCANNER_URL = process.env.SCANNER_BASE_URL || 'http://localhost:8000';

export async function GET(request: Request, { params }: { params: { id: string } }) {
    const id = params.id;
    const res = await fetch(`${SCANNER_URL}/scan/${id}`);

    if (!res.ok) {
        return NextResponse.json({ error: 'Failed to fetch result' }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
}
