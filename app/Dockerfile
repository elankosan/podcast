# syntax=docker/dockerfile:1

# =========================
# Dependencies Stage
# =========================
FROM node:20-alpine AS deps

# Install libc6-compat for Alpine compatibility with some packages
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files and install dependencies (not install, ci for clean lockfile-based install)
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# =========================
# Build Stage
# =========================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build the Next.js application (generates standalone output)
RUN npm run build

# =========================
# Runner Stage
# =========================
FROM node:20-alpine AS runner

# Install curl for healthcheck
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

WORKDIR /app

# Set environment
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Copy standalone output from builder
# Next.js outputs standalone server.js and static files to .next/standalone
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# Switch to non-root user
USER nextjs

# Expose Next.js port
EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000 || exit 1

# Start the standalone server
CMD ["node", "server.js"]
