# ============================================
# Scoop AI Agent V3 - Hybrid Runtime
# Python 3.11 + Node.js (Required for Agent SDK)
# ============================================

FROM python:3.11-slim

WORKDIR /app

# 1. Install System Dependencies & Node.js (Required for Claude Code CLI)
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @anthropic-ai/claude-code && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy Application
COPY . .

# 4. Environment Config
ENV PORT=8080
# Enable SDK File Checkpointing (Optional but recommended)
ENV CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING=1

# 5. Run
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
