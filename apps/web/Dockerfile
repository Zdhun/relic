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
COPY turbo.json turbo.json
RUN pnpm run build --filter=web...

FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
USER nextjs

COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

EXPOSE 3000
ENV PORT 3000
CMD ["node", "apps/web/server.js"]
