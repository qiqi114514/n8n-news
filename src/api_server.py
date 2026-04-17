#!/usr/bin/env python
# -*- coding: utf-8 -*-
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
import os
import logging
from urllib.parse import parse_qs

# 配置日志
LOG_FILE = '/app/api_server.log' if os.path.exists('/app') else 'api_server.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)

SCRIPT_MAP = {
    "run_crawler": "runner.py",
    "save_raw": "save_raw.py"
}

class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        try:
            response = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            logging.error(f"Send Error: {e}")

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            params = json.loads(post_data) if post_data else {}
        except:
            params = parse_qs(post_data)

        script_key = params.get("script", ["run_crawler"])[0] if isinstance(params.get("script"), list) else params.get("script", "run_crawler")
        
        if script_key not in SCRIPT_MAP:
            return self._send_json({"error": f"Script {script_key} not found"}, 404)

        script_path = os.path.join(os.path.dirname(__file__), SCRIPT_MAP[script_key])
        
        # 获取 count 参数，默认 5
        count = params.get("count", 10)
        source = params.get("source", "all")

        try:
            logging.info(f"🚀 Running {script_key} for {source} (count={count})")
            
            # 执行命令
            cmd = [sys.executable, script_path, "--source", str(source), "-n", str(count)]
            proc = subprocess.run(cmd, capture_output=True, timeout=600)
            
            stdout_text = proc.stdout.decode('utf-8', errors='replace').strip()
            
            # 找到 JSON 部分（防止有杂质字符）
            if "[" in stdout_text:
                json_start = stdout_text.find("[")
                json_end = stdout_text.rfind("]") + 1
                final_result = json.loads(stdout_text[json_start:json_end])
            else:
                final_result = {"raw_output": stdout_text}

            # --- 修改后的限制逻辑：放宽到 100 条 ---
            if isinstance(final_result, list):
                if len(final_result) > 100:
                    final_result = final_result[:100]
            elif isinstance(final_result, dict) and "news_list" in final_result:
                if len(final_result["news_list"]) > 100:
                    final_result["news_list"] = final_result["news_list"][:100]

            if proc.returncode == 0:
                self._send_json(final_result, 200)
            else:
                self._send_json({"error": "Failed", "stderr": proc.stderr.decode()}, 500)
                
        except subprocess.TimeoutExpired:
            self._send_json({"error": "Timeout"}, 504)
        except Exception as e:
            logging.error(f"🔥 Error: {e}")
            self._send_json({"error": str(e)}, 500)

    def do_GET(self):
        self._send_json({"status": "running", "endpoints": ["/ (POST only)"]})

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), APIHandler)
    print("✅ API Server started on port 8000...")
    server.serve_forever()