import multiprocessing

# A string of the form "HOST:PORT" to bind.

bind = "0.0.0.0:8000"

# The maximum number of pending connections.
backlog = 2048

# Set the number of Gunicorn worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# The type of workers to use.
worker_class = "uvicorn.workers.UvicornWorker"

# The maximum number of simultaneous clients.
worker_connections = 1500

# Workers silent for more than this many seconds are killed and restarted.
timeout = 120

# Load application code before the worker processes are forked.
preload_app = True


def when_ready(server):
    server.log.info("Server is ready. Spawning workers")
