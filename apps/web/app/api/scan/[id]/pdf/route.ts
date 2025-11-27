import { NextResponse } from 'next/server';

const SCANNER_URL = process.env.SCANNER_BASE_URL || 'http://localhost:8000';

export async function GET(request: Request, { params }: { params: { id: string } }) {
    const id = params.id;
    const res = await fetch(`${SCANNER_URL}/scan/${id}/report.pdf`);

    if (!res.ok) {
        return NextResponse.json({ error: 'Failed to fetch PDF' }, { status: res.status });
    }

    const blob = await res.blob();
    return new NextResponse(blob, {
        headers: {
            'Content-Type': 'application/pdf',
            'Content-Disposition': `attachment; filename=report_${id}.pdf`,
        }
    });
}
