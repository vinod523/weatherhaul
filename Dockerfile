FROM node:22-slim AS frontend
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY index.html vite.config.js ./
COPY frontend ./frontend
RUN pnpm run build
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY --from=frontend /app/dist ./dist
RUN python backend/manage.py collectstatic --noinput
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 180"]
