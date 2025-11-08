# Proxmox to Discord Backup Notifications Setup

## Overview
This setup forwards Proxmox backup notifications to a Discord channel using a simple Python bridge script.

---

## Step 1: Get Your Discord Webhook URL

1. Open your Discord server
2. Right-click the channel where you want notifications
3. Click **Edit Channel** → **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Name it "Proxmox Backups"
6. Click **Copy Webhook URL**
7. Save this URL - you'll need it in Step 2

---

## Step 2: Create the Bridge Script

SSH into your Proxmox server and create the script:

```bash
nano /opt/proxmox-discord-bridge.py
```

Paste this code (replace `YOUR_DISCORD_WEBHOOK_URL` with your actual webhook from Step 1):

```python
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
```

Save and exit (Ctrl+O, Enter, Ctrl+X)

Make it executable:
```bash
chmod +x /opt/proxmox-discord-bridge.py
```

---

## Step 3: Create Systemd Service

```bash
nano /etc/systemd/system/proxmox-discord-bridge.service
```

Paste this:

```ini
[Unit]
Description=Proxmox to Discord Bridge
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt
ExecStart=/usr/bin/python3 /opt/proxmox-discord-bridge.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit (Ctrl+X, Y, Enter)

---

## Step 4: Start the Service

```bash
systemctl daemon-reload
systemctl enable proxmox-discord-bridge
systemctl start proxmox-discord-bridge
systemctl status proxmox-discord-bridge
```

You should see "active (running)" in green.

---

## Step 5: Configure Proxmox Notification Target

1. Open Proxmox web UI
2. Go to **Datacenter** → **Notifications**
3. Click **Add** → **Gotify**
4. Fill in:
   - **Name**: `discord-backup`
   - **Server**: `http://127.0.0.1:8080`
   - **Token**: `messages` (or any text)
5. Click **Add**
6. Select `discord-backup` and click **Test**
7. Check Discord - you should see a test notification!

---

## Step 6: Configure Notification Matcher

Edit the notifications configuration to route backup notifications to Discord:

```bash
nano /etc/pve/notifications.cfg
```

Find the `matcher: default-matcher` section and add `discord-backup` as a target. It should look like this:

```
matcher: default-matcher
        comment Route all notifications to mail-to-root and discord
        mode all
        target mail-to-root
        target discord-backup
```

Save and exit (Ctrl+O, Enter, Ctrl+X)

---

## Step 7: Configure Backup Jobs

1. Go to **Datacenter** → **Backup**
2. Edit your backup job
3. In the **General** tab, find **Notification mode**
4. Set it to **Notification system**
5. Click **OK**

**Note:** You don't need to select a specific target - the matcher from Step 6 will automatically route notifications to Discord.

---
