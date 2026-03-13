import functools
import inspect
import logging
import time
from typing import Any, Dict, Union

from core.logger_factory import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


class ParamRef:
    """用于引用函数参数或对象属性的类"""

    def __init__(self, param_expression: str):
        """
        初始化参数引用

        param_expression: 参数表达式，例如 "task.task_id" 或 "user.name"
        """
        parts = param_expression.split('.', 1)
        self.param_name = parts[0]
        self.attr_path = parts[1] if len(parts) > 1 else None

    def resolve(self, args_dict: Dict[str, Any]) -> Any:
        """从参数字典中解析引用的值"""
        if self.param_name not in args_dict:
            raise ValueError(f"Parameter '{self.param_name}' not founded in args_dict")

        value = args_dict[self.param_name]

        # 如果指定了属性路径，递归获取属性值
        if self.attr_path:
            attrs = self.attr_path.split('.')
            for attr in attrs:
                if hasattr(value, attr):
                    value = getattr(value, attr)
                elif isinstance(value, dict) and attr in value:
                    value = value[attr]
                else:
                    raise ValueError(f"Object '{self.param_name}' no attribute '{attr}'")

        return value

    def __repr__(self) -> str:
        if self.attr_path:
            return f"${{{self.param_name}.{self.attr_path}}}"
        return f"${{{self.param_name}}}"


def log_execution_time(**custom_params: Union[Any, ParamRef]):
    """
    支持引用函数参数和对象属性的执行时间日志装饰器

    使用示例：
    @log_execution_time(task_id=ref("task.task_id"), user=ref("user.name"))
    def process_task(task, user):
        pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数签名并绑定实际参数
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            args_dict = bound_args.arguments

            # 解析自定义参数中的引用
            resolved_params = {}
            for key, value in custom_params.items():
                if isinstance(value, ParamRef):
                    try:
                        resolved_params[key] = value.resolve(args_dict)
                    except Exception as e:
                        resolved_params[key] = f"[RefError: {str(e)}]"
                else:
                    resolved_params[key] = value

            # 执行函数并计时
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()

            # 格式化函数参数
            # args_repr = [repr(a) for a in args]
            # kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            # func_args = ", ".join(args_repr + kwargs_repr)

            # 格式化已解析的自定义参数
            custom_info = ", ".join(f"{k}={v!r}" for k, v in resolved_params.items())

            logging.debug(
                f"Function [{func.__name__}({custom_info})] "
                f"execute elapsed time: {end_time - start_time:.4f} seconds."
            )
            return result

        return wrapper

    return decorator


# 快捷创建参数引用的辅助函数 - 现在支持 "obj.attr" 格式
def ref(param_expression: str) -> ParamRef:
    """创建参数引用，支持 'param_name' 或 'param_name.attr.subattr' 格式"""
    return ParamRef(param_expression)

# ===== 使用示例 =====
# class Task:
#     def __init__(self, task_id: int, title: str):
#         self.task_id = task_id
#         self.title = title
#
#
# @log_execution_time(
#     task_id=ref("task.task_id"),  # 引用 task 对象的 task_id 属性
# )
# def process_task(task: Task):
#     time.sleep(0.5)
#     return task.task_id
#
#
# # 测试调用
# task = Task(123, "数据导入")
# process_task(task)
