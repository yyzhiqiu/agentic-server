FROM node:20-alpine AS build

ARG PNPM_VERSION=9.15.0
ARG VITE_APP_NAME=
ARG VITE_API_BASE_URL=
ARG VITE_API_PREFIX=/v1

ENV VITE_APP_NAME=${VITE_APP_NAME} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_API_PREFIX=${VITE_API_PREFIX}

WORKDIR /app
RUN corepack enable && corepack prepare pnpm@${PNPM_VERSION} --activate

COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf && \
    printf '%s\n' \
      'server {' \
      '    listen 80;' \
      '    server_name _;' \
      '    root /usr/share/nginx/html;' \
      '    index index.html;' \
      '' \
      '    location / {' \
      '        try_files $uri $uri/ /index.html;' \
      '    }' \
      '}' > /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
