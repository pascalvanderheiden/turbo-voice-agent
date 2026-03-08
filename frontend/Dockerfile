FROM node:22-alpine AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
# Build with placeholders — replaced at runtime by entrypoint
ENV NEXT_PUBLIC_API_URL=__NEXT_PUBLIC_API_URL_PLACEHOLDER__
ENV NEXT_PUBLIC_ENTRA_CLIENT_ID=__NEXT_PUBLIC_ENTRA_CLIENT_ID_PLACEHOLDER__
ENV NEXT_PUBLIC_ENTRA_TENANT_ID=__NEXT_PUBLIC_ENTRA_TENANT_ID_PLACEHOLDER__
ENV NEXT_PUBLIC_ENTRA_REDIRECT_URI=__NEXT_PUBLIC_ENTRA_REDIRECT_URI_PLACEHOLDER__
RUN npm run build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --chown=nextjs:nodejs entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["./entrypoint.sh"]
