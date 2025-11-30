/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    async rewrites() {
        return [
            {
                source: '/api/scan/:path*',
                destination: process.env.SCANNER_BASE_URL ? `${process.env.SCANNER_BASE_URL}/scan/:path*` : 'http://scanner:8000/scan/:path*',
            },
            {
                source: '/api/ai/:path*',
                destination: process.env.SCANNER_BASE_URL ? `${process.env.SCANNER_BASE_URL}/api/ai/:path*` : 'http://scanner:8000/api/ai/:path*',
            },
        ];
    },
};

module.exports = nextConfig;
