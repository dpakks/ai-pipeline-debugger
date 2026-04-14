# -----------------------------------------------
# Stage 1: Builder — install dependencies
# -----------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY app/requirements.txt .

RUN pip install --no-cache-dir --target /build/deps -r requirements.txt

# -----------------------------------------------
# Stage 2: Production — slim Lambda runtime image
# -----------------------------------------------
FROM public.ecr.aws/lambda/python:3.12

# Copy installed dependencies from builder stage
COPY --from=builder /build/deps ${LAMBDA_TASK_ROOT}

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}

# Lambda entry point — file.function
CMD ["handler.handler"]