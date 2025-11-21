import importlib
import os
from typing import List

from fastapi import FastAPI, APIRouter
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from core.logger_factory import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


class RouteScanner:
    def __init__(self, app: FastAPI, base_path: str):
        self._app = app
        self._project_path = base_path
        self._project_package = os.path.basename(base_path)
        self._routers: List[APIRouter] = []

        # 初始化Vue应用
        self._init_vue_app(app)

    def _init_vue_app(self, app: FastAPI):
        self._app.mount(
            "/static",
            StaticFiles(directory=f"{self._project_path}/static"),
            name="static")

        @app.get("/", include_in_schema=False)
        def redirect_swagger():
            swagger_url = app.url_path_for("swagger_ui_html")
            return RedirectResponse(url=swagger_url)

    def register_routers(self):
        """将收集到的APIRouter注册到FastAPI应用"""
        self._scan_directory()
        for router in self._routers:
            self._app.include_router(router)

    def _scan_directory(self):
        """递归扫描目录，查找所有routes.py文件并注册路由"""
        for root, dirs, files in os.walk(self._project_path):
            if "routes.py" in files:
                rel_path = os.path.relpath(root, self._project_path)
                if rel_path == ".":
                    module_name = "routes"
                else:
                    module_name = rel_path.replace(os.path.sep, ".") + ".routes"

                full_module_name = f"{self._project_package}.{module_name}"
                try:
                    module = importlib.import_module(full_module_name)
                    # 查找模块中的所有APIRouter实例
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, APIRouter):
                            self._routers.append(attr)
                    logger.info(f"successfully import routes module: {full_module_name}")
                except Exception as e:
                    logger.error(f"failed to import routes module: {full_module_name}, error: {e}")
                    raise e
