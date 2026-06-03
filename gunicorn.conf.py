import os

bind = "unix:/home/deploy/apps/InventarioGLTEC/InventarioGLTEC.sock"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
worker_class = "sync"
worker_tmp_dir = "/dev/shm"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/home/deploy/apps/InventarioGLTEC/logs/access.log"
errorlog = "/home/deploy/apps/InventarioGLTEC/logs/error.log"
loglevel = "info"
capture_output = True
umask = 0o007
