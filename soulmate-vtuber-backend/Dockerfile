# --- Build Stage ---
# Use an official Python runtime as a parent image
FROM python:3.11-slim as builder

# Set the working directory in the container
WORKDIR /app

# Install poetry, pinning the version for reproducible builds
# Use --no-cache-dir to keep the image layer small
RUN pip install --no-cache-dir poetry==1.7.1

# Copy only the dependency definition files
COPY pyproject.toml poetry.lock* ./

# Install dependencies using poetry, without installing the project root
# and without development dependencies. This leverages Docker layer caching.
RUN poetry install --no-root --no-dev

# --- Final Stage ---
# Start from a clean, small base image
FROM python:3.11-slim

# Set environment variables for python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /.venv

# Add the venv to the PATH, so commands can be run directly
ENV PATH="/app/.venv/bin:$PATH"

# Create a non-root user and switch to it for security
RUN useradd --create-home appuser
USER appuser

# Copy the application source code
COPY ./app ./app

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
