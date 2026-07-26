"""
AI Prompt模板服务
提供模板的CRUD操作
"""
from typing import Optional, List, Dict, Any
import json

from src.utils.database import get_db_session
from sqlalchemy import text


class PromptTemplateService:
    """AI Prompt模板服务"""

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """获取所有模板"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT id, template_type, name, content, variables, description, is_active, created_at, updated_at
                    FROM ai_prompt_template
                    ORDER BY template_type
                """)
            ).fetchall()

            templates = []
            for row in result:
                templates.append({
                    "id": row[0],
                    "template_type": row[1],
                    "name": row[2],
                    "content": row[3],
                    "variables": json.loads(row[4]) if isinstance(row[4], str) else row[4],
                    "description": row[5],
                    "is_active": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None,
                })
            return templates

    def get_template_by_type(self, template_type: str) -> Optional[Dict[str, Any]]:
        """根据类型获取模板"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT id, template_type, name, content, variables, description, is_active, created_at, updated_at
                    FROM ai_prompt_template
                    WHERE template_type = :template_type
                """),
                {"template_type": template_type}
            ).fetchone()

            if not result:
                return None

            return {
                "id": result[0],
                "template_type": result[1],
                "name": result[2],
                "content": result[3],
                "variables": json.loads(result[4]) if isinstance(result[4], str) else result[4],
                "description": result[5],
                "is_active": result[6],
                "created_at": result[7].isoformat() if result[7] else None,
                "updated_at": result[8].isoformat() if result[8] else None,
            }

    def update_template(
        self,
        template_type: str,
        name: str,
        content: str,
        variables: List[str],
        description: str
    ) -> bool:
        """更新模板"""
        # 清除缓存
        self._clear_cache(template_type)

        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE ai_prompt_template
                    SET name = :name,
                        content = :content,
                        variables = :variables::jsonb,
                        description = :description,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE template_type = :template_type
                """),
                {
                    "template_type": template_type,
                    "name": name,
                    "content": content,
                    "variables": json.dumps(variables),
                    "description": description,
                }
            )
            return result.rowcount > 0

    def toggle_active(self, template_type: str, is_active: bool) -> bool:
        """切换模板激活状态"""
        # 清除缓存
        if not is_active:
            self._clear_cache(template_type)

        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE ai_prompt_template
                    SET is_active = :is_active,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE template_type = :template_type
                """),
                {
                    "template_type": template_type,
                    "is_active": is_active,
                }
            )
            return result.rowcount > 0

    def _clear_cache(self, template_type: str) -> None:
        """清除模板缓存"""
        from src.services.ai_analysis_service import _template_cache
        if template_type in _template_cache:
            del _template_cache[template_type]


# 全局单例
_prompt_template_service: Optional[PromptTemplateService] = None


def get_prompt_template_service() -> PromptTemplateService:
    """获取Prompt模板服务单例"""
    global _prompt_template_service
    if _prompt_template_service is None:
        _prompt_template_service = PromptTemplateService()
    return _prompt_template_service