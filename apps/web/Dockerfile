FROM node:18-alpine AS base

FROM base AS builder
WORKDIR /app
RUN npm install -g pnpm@8.15.4 turbo
COPY . .
RUN turbo prune --scope=web --docker

FROM base AS installer
WORKDIR /app
RUN npm install -g pnpm@8.15.4
COPY --from=builder /app/out/json/ .
COPY --from=builder /app/out/pnpm-lock.yaml ./
RUN pnpm install

COPY --from=builder /app/out/full/ .
COPY --from=builder /app/turbo.json ./turbo.json

# Set the scanner URL for the build (rewrites are evaluated at build time)
# Note: SCANNER_BASE_URL must be declared in turbo.json globalEnv for this to work
RUN rm -rf apps/web/.next && \
    npm install -g turbo && \
    export SCANNER_BASE_URL=http://scanner:8000 && \
    turbo run build --filter=web... --force


FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

# Copy the standalone output - the structure preserves the monorepo layout
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

EXPOSE 3000
ENV PORT 3000
# With outputFileTracingRoot, server.js is at apps/web/server.js
CMD ["node", "apps/web/server.js"]
