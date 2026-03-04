FROM node:22-alpine AS base

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Development stage
FROM base AS development

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

# Production build
FROM base AS builder

COPY . .
RUN npm run build

# Production stage
FROM node:22-alpine AS production

WORKDIR /app

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
