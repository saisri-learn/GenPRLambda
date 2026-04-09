# Multi-stage build for AWS Lambda with Python 3.11 and Node.js 20
# This container includes both runtimes to support MCP server (Node.js) and Lambda handler (Python)

FROM public.ecr.aws/lambda/python:3.11 AS base

# Install Node.js 20.x
RUN curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    yum install -y nodejs && \
    yum clean all && \
    rm -rf /var/cache/yum

# Verify installations
RUN python --version && node --version && npm --version

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy package files first (for better caching)
COPY requirements.txt package.json ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js dependencies (REPO MCP server)
RUN npm install --production && npm cache clean --force

# Copy source code
COPY src/ ./src/

# Set Python path
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Set Lambda handler
CMD ["src.lambda_function.lambda_handler"]
