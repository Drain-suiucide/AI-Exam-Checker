# Стадия сборки: Node LTS, установка зависимостей точно из lock-файла.
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-fund --no-audit

COPY . .
RUN npm run build

# Стадия отдачи: nginx отдаёт статику SPA и проксирует /api на backend
# (единый origin — без CORS, ADR-001).
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://localhost/health || exit 1
