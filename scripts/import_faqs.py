import json
import argparse
import requests
from typing import List, Dict, Any


def create_index(host: str, user: str, password: str, index: str):
    """创建FAQ索引"""
    headers = {"Content-Type": "application/json"}
    auth = (user, password)

    # 设置索引映射
    mapping = {
        "mappings": {
            "properties": {
                "question": {"type": "text", "analyzer": "standard"},
                "answer": {"type": "text", "analyzer": "standard"}
            }
        }
    }

    # 删除已存在的索引
    requests.delete(f"{host}/{index}", auth=auth, headers=headers)

    # 创建新索引
    response = requests.put(
        f"{host}/{index}",
        auth=auth,
        headers=headers,
        data=json.dumps(mapping)
    )

    print(f"创建索引结果: {response.status_code} - {response.text}")


def import_faqs(host: str, user: str, password: str, index: str, faqs: List[Dict[str, Any]]):
    """导入FAQ数据"""
    headers = {"Content-Type": "application/json"}
    auth = (user, password)

    # 批量导入数据
    bulk_data = []
    for faq in faqs:
        bulk_data.append({"index": {"_index": index}})
        bulk_data.append(faq)

    bulk_body = "\n".join(json.dumps(item) for item in bulk_data) + "\n"

    response = requests.post(
        f"{host}/_bulk",
        auth=auth,
        headers=headers,
        data=bulk_body
    )

    print(f"导入数据结果: {response.status_code}")
    if response.status_code != 200:
        print(f"错误: {response.text}")
    else:
        print(f"成功导入 {len(faqs)} 条FAQ数据")


def main():
    parser = argparse.ArgumentParser(description="导入FAQ数据到Elasticsearch")
    parser.add_argument("--host", default="http://localhost:9200", help="Elasticsearch主机地址")
    parser.add_argument("--user", default="elastic", help="用户名")
    parser.add_argument("--password", required=True, help="密码")
    parser.add_argument("--index", default="faqs", help="索引名称")
    parser.add_argument("--file", required=True, help="FAQ JSON文件路径")

    args = parser.parse_args()

    # 读取FAQ数据
    with open(args.file, "r", encoding="utf-8") as f:
        faqs = json.load(f)

    # 创建索引
    create_index(args.host, args.user, args.password, args.index)

    # 导入数据
    import_faqs(args.host, args.user, args.password, args.index, faqs)


if __name__ == "__main__":
    main()