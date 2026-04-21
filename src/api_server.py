#!/usr/bin/env python
# -*- coding: utf-8 -*-
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
import os
import logging

LOG_FILE = '/app/api_server.log' if os.path.exists('/app') else 'api_server.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

SCRIPT_MAP = {
    "run_crawler": "runner.py",
    "save_raw": "save_raw.py",
    "check_exists": "check_exists.py",
    "preprocess": "preprocess.py",
    "query_pending": "query_pending.py",
    "save_analysis": "save_analysis.py",
    "save_report" : "save_report.py",
    "query_subscriptions" : "query_subscriptions.py"
}

class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        # 接收 n8n 发来的 JSON 数组
        post_data = self.rfile.read(content_length)
        
        # 这里的逻辑是：根据路径运行对应的脚本
        path = self.path.strip('/')
        script_to_run = SCRIPT_MAP.get(path, "check_exists.py") # 默认查重

        try:
            logging.info(f"🚀 Running {script_to_run} with data size: {content_length}")
            
            # 使用 Popen 和 communicate 处理大数据传输，防止 socket hang up
            proc = subprocess.Popen(
                [sys.executable, script_to_run],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 将 n8n 传来的 post_data 注入脚本 stdin，并获取结果
            stdout_data, stderr_data = proc.communicate(input=post_data, timeout=200)
            
            if proc.returncode == 0:
                # 解析脚本输出并返回给 n8n
                try:
                    result = json.loads(stdout_data.decode('utf-8'))
                except json.JSONDecodeError:
                    # 如果脚本返回的是纯文本而非JSON，将其包装成JSON格式
                    result = {"output": stdout_data.decode('utf-8')}
                self._send_json(result, 200)
            else:
                # Log the actual error for debugging
                error_message = stderr_data.decode('utf-8')
                logging.error(f"Script failed with return code {proc.returncode}: {error_message}")
                self._send_json({"error": error_message}, 500)
                
        except subprocess.TimeoutExpired:
            logging.error("⏰ Script execution timed out")
            self._send_json({"error": "Script execution timed out"}, 504)
        except Exception as e:
            logging.error(f"🔥 Server Error: {e}")
            self._send_json({"error": str(e)}, 500)

if __name__ == '__main__':
    # Start the HTTP server
    port = int(os.environ.get('PORT', 8000))
    server_address = ('0.0.0.0', port)  # Listen on all interfaces
    
    httpd = HTTPServer(server_address, APIHandler)
    
    print(f'Starting server on port {port}...')
    httpd.serve_forever()