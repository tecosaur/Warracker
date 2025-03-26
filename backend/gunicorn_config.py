#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gunicorn configuration file for Warracker application.
This ensures scheduler only runs in one worker process.
"""

import os
import multiprocessing

# Server configurations
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync" 
timeout = 120
keepalive = 5

# Set worker environment variables
def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"Worker {worker.pid} received SIGINT/SIGQUIT")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    print(f"Worker {worker.pid} received SIGABRT")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    print(f"Worker {worker.pid} exited")

def on_starting(server):
    """Called just before the master process is initialized."""
    print("Server is starting")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    os.environ["GUNICORN_WORKER_ID"] = str(worker.age - 1)  # Worker ID starts at 0
    os.environ["GUNICORN_WORKER_PROCESS_NAME"] = f"worker-{worker.age - 1}"
    os.environ["GUNICORN_WORKER_CLASS"] = worker_class
    
    print(f"Worker {worker.pid} (ID: {worker.age - 1}) forked")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    print(f"Forking worker #{worker.age}")

print(f"Gunicorn configuration loaded with {workers} workers") 