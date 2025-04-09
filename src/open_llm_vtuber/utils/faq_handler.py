from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


class FAQHandler:
    """
    FAQ处理模块，根据匹配度处理用户查询
    """

    def __init__(self, es_search):
        """
        初始化FAQ处理器

        Args:
            es_search: Elasticsearch搜索实例
        """
        self.es_search = es_search

    async def process_query(self, query: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        处理用户查询，根据匹配度返回不同的结果

        Args:
            query: 用户查询

        Returns:
            Tuple[Optional[str], Optional[str], float]:
                - 直接回答（高匹配时）
                - 增强提示（中等匹配时）
                - 匹配度
        """
        if not query or not self.es_search:
            return None, None, 0.0

        try:
            best_match, candidates = self.es_search.get_best_match(query)

            if not best_match:
                logger.info(f"未找到匹配FAQ: {query}")
                return None, None, 0.0

            similarity = best_match.get("similarity", 0.0)
            logger.info(f"FAQ匹配度: {similarity:.2f}, 问题: {best_match['question']}")

            # 高匹配度(>=0.9)：直接返回答案
            if similarity >= 0.9:
                logger.info(f"高匹配度: {similarity:.2f}, 直接返回FAQ答案")
                return best_match["answer"], None, similarity

            # 中等匹配度(0.7-0.9)：增强提示，针对前5个答案整理输出
            elif similarity >= 0.7:
                logger.info(f"中等匹配度: {similarity:.2f}, 增强LLM提示")
                # 构建增强提示
                enhanced_prompt = self._build_enhanced_prompt(query, best_match, candidates)
                return None, enhanced_prompt, similarity

            # 低匹配度(<0.7)：大模型自己思考的答案
            else:
                logger.info(f"低匹配度: {similarity:.2f}, 使用LLM直接回答")
                return None, None, similarity

        except Exception as e:
            logger.error(f"处理FAQ查询时发生错误: {e}")
            return None, None, 0.0

    def _build_enhanced_prompt(self, query: str, best_match: Dict[str, Any],
                               candidates: List[Dict[str, Any]]) -> str:
        """
        构建增强提示

        Args:
            query: 用户查询
            best_match: 最佳匹配
            candidates: 候选匹配

        Returns:
            str: 增强提示
        """
        prompt = (
            f"用户问题: {query}\n\n"
            f"以下是一些相关的FAQ信息，请参考这些信息给出准确、综合的回答：\n\n"
            f"最佳匹配问题: {best_match['question']}\n"
            f"参考答案: {best_match['answer']}\n\n"
        )

        if candidates:
            prompt += "其他相关信息:\n"
            for i, candidate in enumerate(candidates):
                prompt += f"{i + 1}. 问题: {candidate['question']}\n   答案: {candidate['answer']}\n\n"

        prompt += "请根据以上所有相关信息，综合整理出完整的回答，以友好专业的口吻回答用户的问题。如果上述信息有冲突，请基于最相关的信息进行回答。如果以上信息不足以回答用户问题，请根据你的知识给出最佳回答。"

        return prompt