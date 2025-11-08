#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import sys
import traceback

DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK_URL"
PORT = 8080

class ProxmoxHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        print(f"Received POST request to {self.path}")
        
        try:
            # Handle chunked transfer encoding
            if self.headers.get('Transfer-Encoding', '').lower() == 'chunked':
                print("Processing chunked data")
                chunks = []
                while True:
                    line = self.rfile.readline().strip()
                    chunk_size = int(line, 16)
                    if chunk_size == 0:
                        break
                    chunks.append(self.rfile.read(chunk_size))
                    self.rfile.readline()  # Read trailing CRLF
                post_data = b''.join(chunks)
            else:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
            
            print(f"Raw data received: {post_data}")
            
            data = json.loads(post_data.decode('utf-8'))
            print(f"Parsed JSON: {data}")
            
            title = data.get('title', 'Proxmox Notification')
            message = data.get('message', '')
            priority = data.get('priority', 5)
            
            print(f"Title: {title}, Message: {message}, Priority: {priority}")
            
            # Determine color based on priority or content
            if priority >= 8 or 'error' in title.lower() or 'fail' in title.lower():
                color = 15158332  # Red
                emoji = "❌"
            elif 'success' in title.lower() or 'completed' in title.lower() or 'finish' in title.lower():
                color = 3066993  # Green
                emoji = "✅"
            else:
                color = 16776960  # Yellow
                emoji = "ℹ️"
            
            discord_payload = {
                "embeds": [{
                    "title": f"{emoji} {title}",
                    "description": message[:2000] if message else "No details provided",
                    "color": color,
                    "footer": {"text": "Proxmox Backup Notification"}
                }]
            }
            
            print(f"Sending to Discord")
            
            req = urllib.request.Request(
                DISCORD_WEBHOOK,
                data=json.dumps(discord_payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'ProxmoxDiscordBot/1.0'
                }
            )
            
            with urllib.request.urlopen(req) as response:
                resp_data = response.read()
                print(f"Discord response: {resp_data}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            
            print(f"Successfully forwarded: {title}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "error"}')
    
    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

if __name__ == '__main__':
    print(f"Starting Proxmox-Discord bridge on port {PORT}")
    sys.stdout.flush()
    server = HTTPServer(('0.0.0.0', PORT), ProxmoxHandler)
    server.serve_forever()
