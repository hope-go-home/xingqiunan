# 用户偏好管理器：跨会话长期记忆的 CRUD

from sqlalchemy import select, delete
from app.core.database import async_session
from app.models.user_preference import UserPreference


async def load_preferences(user_id: int) -> dict[str, str]:
    """加载用户所有偏好"""
    async with async_session() as db:
        rows = await db.execute(
            select(UserPreference.key, UserPreference.value)
            .where(UserPreference.user_id == user_id)
        )
        return {row.key: row.value for row in rows.all()}


async def set_preference(user_id: int, key: str, value: str) -> str:
    """设置偏好（已存在则更新）"""
    key = key.strip().lower()
    value = value.strip()
    if not key or not value:
        return "key 和 value 不能为空"
    if len(key) > 50:
        return "key 不能超过 50 个字符"

    async with async_session() as db:
        row = await db.execute(
            select(UserPreference)
            .where(UserPreference.user_id == user_id, UserPreference.key == key)
        )
        existing = row.scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(UserPreference(user_id=user_id, key=key, value=value))
        await db.commit()
    return f"已设置：{key} = {value}"


async def delete_preference(user_id: int, key: str) -> str:
    """删除指定偏好"""
    key = key.strip().lower()
    async with async_session() as db:
        await db.execute(
            delete(UserPreference)
            .where(UserPreference.user_id == user_id, UserPreference.key == key)
        )
        await db.commit()
    return f"已删除：{key}"


async def clear_preferences(user_id: int) -> str:
    """清空所有偏好"""
    async with async_session() as db:
        await db.execute(
            delete(UserPreference).where(UserPreference.user_id == user_id)
        )
        await db.commit()
    return "已清空所有偏好"


def format_preferences(prefs: dict[str, str]) -> str:
    """格式化偏好为 prompt 片段"""
    if not prefs:
        return ""
    lines = [f"{k}={v}" for k, v in sorted(prefs.items())]
    return "用户偏好：" + "，".join(lines)


def parse_preference_command(user_input: str) -> tuple[str, dict] | None:
    """
    解析偏好命令，返回 (action, params)
    支持：
      记住：key=value / 记住：key value
      修改：key=value / 修改：key value
      删除偏好：key
      查看偏好
      清空偏好
    """
    text = user_input.strip()

    # 记住 / 设置
    for prefix in ("记住：", "记住:", "设置：", "设置:"):
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            if "=" in rest:
                k, v = rest.split("=", 1)
                return ("set", {"key": k.strip(), "value": v.strip()})
            parts = rest.split(maxsplit=1)
            if len(parts) == 2:
                return ("set", {"key": parts[0].strip(), "value": parts[1].strip()})
            return ("set", {"key": parts[0].strip(), "value": "true"})

    # 修改（等同于设置）
    for prefix in ("修改：", "修改:"):
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            if "=" in rest:
                k, v = rest.split("=", 1)
                return ("set", {"key": k.strip(), "value": v.strip()})
            parts = rest.split(maxsplit=1)
            if len(parts) == 2:
                return ("set", {"key": parts[0].strip(), "value": parts[1].strip()})

    # 删除偏好
    for prefix in ("删除偏好：", "删除偏好:", "取消记住：", "取消记住:"):
        if text.startswith(prefix):
            key = text[len(prefix):].strip()
            return ("delete", {"key": key})

    # 查看偏好
    if text in ("查看偏好", "显示偏好", "我的偏好", "偏好列表"):
        return ("list", {})

    # 清空偏好
    if text in ("清空偏好", "清除偏好", "重置偏好"):
        return ("clear", {})

    return None
