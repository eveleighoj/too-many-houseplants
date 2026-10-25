# The trips frontend as a container: the static build served by nginx. Production uses Render's
# static hosting instead (render.yaml); this image is for running the built site locally or in
# e2e tests. Build from the repo root:
#   docker build -f services/trips-frontend/Dockerfile --build-arg VITE_API_URL=... .
FROM node:24-slim AS build
WORKDIR /repo
# Every workspace manifest, so `npm ci` matches the root lockfile; then only this app's source.
COPY package.json package-lock.json ./
COPY services/trips-frontend/package.json services/trips-frontend/
RUN npm ci
COPY services/trips-frontend services/trips-frontend
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build -w services/trips-frontend


FROM nginx:1.27-alpine AS runtime
COPY docker/nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/services/trips-frontend/build /usr/share/nginx/html
