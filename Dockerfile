FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_BASE_PATH="/apihubnoreview"
RUN npm run build

FROM node:20-slim

WORKDIR /app

# Install Python
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend build
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/
COPY --from=frontend-build /app/frontend/next.config.mjs ./frontend/
COPY --from=frontend-build /app/frontend/node_modules ./frontend/node_modules

# Copy startup script
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8080

CMD ["./start.sh"]
