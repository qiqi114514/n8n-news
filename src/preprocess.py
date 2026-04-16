import json
import sys

def main():
    try:
        # 从 stdin 读取数据（n8n 传过来的原始内容）
        raw_input = sys.stdin.read()
        if not raw_input:
            print(json.dumps({"processed_news": []}))
            return
            
        data = json.loads(raw_input)
        
        # 统一处理输入：兼容列表或带 news_list 键的字典
        news_items = data.get("news_list", []) if isinstance(data, dict) else data
        if not isinstance(news_items, list):
            news_items = []

        processed = []
        for item in news_items:
            processed.append({
                "id": item.get("id"),
                "title": item.get("title", "无标题"),
                "source": item.get("source", "未知信源"),
                "url": item.get("url", ""),
                # 截取正文前 300 字，压缩体积
                "summary": str(item.get("content", ""))[:300].replace("\n", " ") + "..."
            })
            
        # 必须 print 出来，因为 api_server.py 是通过捕获 stdout 来拿结果的
        print(json.dumps({"processed_news": processed}, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()