import os
from typing import Optional

from fastapi import APIRouter

from services import config_manager

router = APIRouter(prefix="/site", tags=["点播接口"])

# 定义分类 ID 映射（横向导航）
_VOD_CATEGORIES = [
    {"type_id": "1", "type_name": "大语文"},
    {"type_id": "2", "type_name": "数学"},
    {"type_id": "3", "type_name": "物理"},
    {"type_id": "4", "type_name": "化学"},
    {"type_id": "5", "type_name": "生物"},
    {"type_id": "6", "type_name": "历史"},
    {"type_id": "7", "type_name": "政治"},
    {"type_id": "8", "type_name": "地理"},
]


def get_category_name(tid):
    for c in _VOD_CATEGORIES:
        if c['type_id'] == tid: return c['type_name']
    return None


@router.get("/vod", summary="查询点播数据")
def get_vod(
    ac: Optional[str] = None,
    t: Optional[str] = None,   # 分类ID
    ids: Optional[str] = None, # 详情ID (格式: 分类/文件名.txt)
    wd: Optional[str] = None,  # 搜索关键词
    pg: int = 1  # 分页
):
    # 1. 返回分类列表
    if not ac:
        return {
            "class": _VOD_CATEGORIES,
            "list": [],
            "total": 0,
            "page": 1,
            "pagecount": 1,
            "limit": 20
        }

    base_dir = config_manager.site_cnconfig.get("base")

    # 2. 点击具体视频进入播放页
    if ac == 'detail' and ids:
        file_path = os.path.join(base_dir, ids)
        if os.path.exists(file_path):
            pic = ""
            content = "暂无简介"
            play_urls = []

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue

                    if line.startswith("PIC$"):
                        pic = line.replace("PIC$", "")
                    elif line.startswith("CONTENT$"):
                        content = line.replace("CONTENT$", "")
                    else:
                        play_urls.append(line)

            return {
                "list": [{
                    "vod_id": ids,
                    "vod_name": ids.split('/')[-1].replace('.txt', ''),
                    "vod_pic": pic or "",
                    "vod_content": content,
                    "vod_play_from": "在线直链",
                    "vod_play_url": "#".join(play_urls)
                }]
            }

    # 3. 当 searchable: 1 时触发
    if wd:
        search_results = []
        for cat in _VOD_CATEGORIES:
            cat_name = cat['type_name']
            path = os.path.join(base_dir, cat_name)
            if os.path.exists(path):
                for fname in os.listdir(path):
                    if wd in fname and fname.endswith('.txt'):
                        search_results.append({
                            "vod_id": f"{cat_name}/{fname}",
                            "vod_name": fname.replace('.txt', ''),
                            "vod_pic": "https://icons8.com"
                        })
        return {"list": search_results}

    # 4. 点击导航栏分类
    if ac == 'list' and t:
        cat_name = get_category_name(t)
        cat_path = os.path.join(base_dir, cat_name)
        vlist = []
        if os.path.exists(cat_path):
            for fname in os.listdir(cat_path):
                if fname.endswith('.txt'):
                    vlist.append({
                        "vod_id": f"{cat_name}/{fname}",
                        "vod_name": fname.replace('.txt', ''),
                        "vod_pic": "https://icons8.com"
                    })
        return {
            "list": vlist,
            "total": len(vlist),
            "page": 1,
            "pagecount": 1,
            "limit": len(vlist)
        }

    return {"list": []}
