# syntax=docker/dockerfile:1

# Use the base Python image
ARG PYTHON_VERSION=3.11.4
FROM python:${PYTHON_VERSION}-slim as base

# needed for gif creation i think
RUN apt-get update && apt-get install -y ffmpeg

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    serveruser

# Set the working directory and assign ownership to the appuser
WORKDIR /app

# Create the /app/instance directory and set permissions (20002 for celery user too)
RUN groupadd instance-users && gpasswd -a serveruser instance-users

RUN mkdir -p /app/instance/temp /app/instance/fontcache && \
    chown -R serveruser:instance-users /app/instance && \
    chmod 775 /app/instance

RUN chmod -R g+w /app/instance

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /home/appuser/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt && \
    chown -R serveruser:serveruser /usr/local/lib/python3.11/site-packages/

# Copy the source code into the container.
COPY . .

# Switch to the non-privileged user to run the application.
USER serveruser

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
# CMD ["gunicorn", "-w", "1", "-b", ":8000", "--certfile=/app/ssl/localhost/certificate.pem", "--keyfile=/app/ssl/localhost/key.pem", "--log-level", "debug", "wsgi:application"]
CMD ["gunicorn", "-w", "1", "-b", ":8000", "--certfile=/app/ssl/usebeatcloud_com.crt", "--keyfile=/app/ssl/usebeatcloud_com.key", "--log-level", "debug", "wsgi:application"]
