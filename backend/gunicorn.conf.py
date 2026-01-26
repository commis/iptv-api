import os

# 获取脚本所在目录（python目录）
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

bind = "0.0.0.0:8001"
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
chdir = project_root
preload_app = True

worker_extra_args = ["--root-path", "/api"]

raw_env = [f"PYTHONPATH={project_root}", "API_PREFIX=/api"]
