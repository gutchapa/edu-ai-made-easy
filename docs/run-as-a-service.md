# Keep the briefing server running

## Linux / Raspberry Pi (systemd)

Install as in the README, under e.g. `/home/pi/edu-ai-made-easy/briefing`, then create
`/etc/systemd/system/muse-briefing.service`:

```ini
[Unit]
Description=Muse morning briefing server
Wants=network-online.target
After=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/edu-ai-made-easy/briefing
ExecStart=/home/pi/edu-ai-made-easy/briefing/.venv/bin/muse-briefing serve -c briefing.toml
# Keep the push token out of the config file if you prefer:
# Environment=BRIEFING_PUSH_TOKEN=change-me
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now muse-briefing
journalctl -u muse-briefing -f
```

## macOS (launchd)

Save as `~/Library/LaunchAgents/ai.muse.briefing.plist`, adjusting the paths:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>ai.muse.briefing</string>
  <key>WorkingDirectory</key><string>/Users/you/edu-ai-made-easy/briefing</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/edu-ai-made-easy/briefing/.venv/bin/muse-briefing</string>
    <string>serve</string><string>-c</string><string>briefing.toml</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardErrorPath</key><string>/tmp/muse-briefing.log</string>
</dict>
</plist>
```

```sh
launchctl load ~/Library/LaunchAgents/ai.muse.briefing.plist
```

Give the server box a fixed LAN IP (a DHCP reservation in your router), so the URL in the
Muse skill keeps working.
