import json
import requests
from typing import List, Dict, Any, Tuple
from loguru import logger


class ESSearch:
    """
    Elasticsearch搜索模块，用于FAQ问题匹配
    """

    def __init__(self, host: str, user: str, password: str, index: str = "faqs"):
        """
        初始化Elasticsearch连接

        Args:
            host: Elasticsearch主机地址
            user: 用户名
            password: 密码
            index: 索引名称
        """
        self.host = host
        self.user = user
        self.password = password
        self.index = index
        self.auth = (user, password)
        self.headers = {"Content-Type": "application/json"}
        self._check_connection()

    def _check_connection(self) -> bool:
        """
        检查Elasticsearch连接
        """
        try:
            response = requests.get(
                f"{self.host}/_cluster/health",
                auth=self.auth,
                headers=self.headers
            )
            if response.status_code == 200:
                logger.info("成功连接到Elasticsearch")
                return True
            else:
                logger.error(f"连接Elasticsearch失败: {response.text}")
                return False
        except Exception as e:
            logger.error(f"连接Elasticsearch时发生错误: {e}")
            return False

    def search_faq(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索FAQ匹配问题

        Args:
            query: 用户查询
            top_k: 返回结果数量

        Returns:
            List[Dict]: 匹配结果列表，每个结果包含问题、答案和分数
        """
        try:
            # 构建查询请求
            search_query = {
                "size": top_k,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["question^3", "answer"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "_source": ["question", "answer"]
            }

            # 发送搜索请求
            response = requests.post(
                f"{self.host}/{self.index}/_search",
                auth=self.auth,
                headers=self.headers,
                data=json.dumps(search_query)
            )

            if response.status_code != 200:
                logger.error(f"搜索请求失败: {response.text}")
                return []

            results = []
            for hit in response.json()["hits"]["hits"]:
                results.append({
                    "question": hit["_source"]["question"],
                    "answer": hit["_source"]["answer"],
                    "score": hit["_score"]
                })

            # 归一化分数到0-1范围
            if results:
                max_score = max(result["score"] for result in results)
                for result in results:
                    result["similarity"] = result["score"] / max_score

            return results

        except Exception as e:
            logger.error(f"搜索FAQ时发生错误: {e}")
            return []

    def get_best_match(self, query: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        获取最佳匹配结果和其他候选结果

        Args:
            query: 用户查询

        Returns:
            Tuple: (最佳匹配, 其他候选结果列表)
        """
        results = self.search_faq(query)
        if not results:
            return None, []

        best_match = results[0]
        candidates = results[1:5] if len(results) > 1 else []

        return best_match, candidates