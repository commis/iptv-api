import os

import uvicorn
from fastapi import FastAPI

from core.logger_factory import LoggerFactory
from utils.scanner import RouteScanner

logger = LoggerFactory.get_logger(__name__)

api_prefix = os.getenv("API_PREFIX", "")


class CreateApplication:
    def __init__(self):
        self._app = FastAPI(
            title="IPTV API文档",
            description="自动生成的API文档",
            version="1.0.0",
            openapi_prefix=api_prefix,
            debug=True)

        # 初始化路由扫描器
        scanner = RouteScanner(self._app, os.path.dirname(os.path.abspath(__file__)))

        # 扫描当前目录下的所有routes.py文件
        scanner.register_routers()

    def get_app(self):
        return self._app

    def start_server(self):
        import __main__ as main
        module_name = os.path.basename(main.__file__).replace('.py', '')
        uvicorn.run(
            f"{module_name}:app",
            host="0.0.0.0",
            port=8001,
            workers=1
        )


logger.info(f"project root: {os.getcwd()}")
application_creator = CreateApplication()
app = application_creator.get_app()

if __name__ == '__main__':
    application_creator.start_server()
