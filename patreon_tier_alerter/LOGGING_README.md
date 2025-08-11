# Patreon Tier Alerter Bot - Logging System

## 🎯 Overview

The bot now includes a comprehensive logging system with file rotation, multiple log levels, and dedicated log files for different types of events.

## 📁 Log Files Structure

```
logs/
├── patreon_bot.log      # Main bot activity (10MB max, keep 5 files)
├── sms_alerts.log       # SMS alert history (5MB max, keep 10 files)
├── errors.log           # Error messages only (5MB max, keep 10 files)
└── patreon_bot.log.1   # Rotated log files (compressed)
```

## 🔍 What Gets Logged

### 📊 Main Bot Activity (`patreon_bot.log`)
- Bot startup and configuration
- Check cycle starts/completions
- Creator monitoring status
- Tier availability changes
- Configuration reloads
- General bot operations

### 📱 SMS Alerts (`sms_alerts.log`)
- **SMS Alert Sent**: `SMS ALERT SENT - Tier: TIER_NAME, Creator: CREATOR_NAME, Phone: +1234567890, Provider: textbelt`
- **SMS Alert Failed**: `SMS ALERT FAILED - Tier: TIER_NAME, Creator: CREATOR_NAME, Phone: +1234567890, Provider: textbelt, Error: ERROR_MESSAGE`
- TextBelt IDs and success/failure details

### ❌ Error Logs (`errors.log`)
- Scraping failures
- SMS sending errors
- Configuration issues
- Network problems
- Any exceptions or errors

### 🎯 Tier Status Changes
- **Tier Available**: `TIER STATUS - CREATOR_NAME: TIER_NAME -> available | URL: URL`
- **Tier Unavailable**: `TIER STATUS - CREATOR_NAME: TIER_NAME -> sold_out | URL: URL`

## 🚀 Log Rotation

### Automatic Rotation
- **Main logs**: 10MB max, keep 5 files
- **SMS logs**: 5MB max, keep 10 files  
- **Error logs**: 5MB max, keep 10 files
- **Compression**: Old logs are automatically compressed

### Manual Rotation
```bash
# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/patreon-bot

# Force rotation
sudo logrotate -f /etc/logrotate.d/patreon-bot
```

## 📋 Viewing Logs

### Real-time Monitoring
```bash
# Follow main logs
tail -f logs/patreon_bot.log

# Follow SMS alerts
tail -f logs/sms_alerts.log

# Follow errors
tail -f logs/errors.log
```

### Historical Analysis
```bash
# View all SMS alerts
cat logs/sms_alerts.log

# Search for specific tier alerts
grep "MICROBATCHES" logs/sms_alerts.log

# View recent errors
tail -100 logs/errors.log

# Search for specific dates
grep "2025-08-11" logs/*.log
```

### SMS Alert History
```bash
# Count total SMS alerts sent
grep "SMS ALERT SENT" logs/sms_alerts.log | wc -l

# View last 10 SMS alerts
grep "SMS ALERT SENT" logs/sms_alerts.log | tail -10

# Search for failed SMS alerts
grep "SMS ALERT FAILED" logs/sms_alerts.log
```

## 🔧 Configuration

### Log Directory
- **Default**: `logs/` (relative to bot directory)
- **Custom**: Modify `LoggerManager(log_dir="custom_path")` in `alerter.py`

### Log Levels
- **INFO**: General bot activity, tier changes, SMS alerts
- **WARNING**: Configuration issues, missing data
- **ERROR**: Failures, exceptions, SMS errors

### Rotation Settings
- **Frequency**: Daily rotation
- **Compression**: Gzip compression for old logs
- **Permissions**: 644 (readable by all, writable by owner)

## 📊 Example Log Entries

### SMS Alert Success
```
2025-08-11 17:30:15 - INFO - SMS ALERT SENT - Tier: MICROBATCHES, Creator: Drums and Drams, Phone: +16023501188, Provider: textbelt
```

### Tier Status Change
```
2025-08-11 17:30:15 - INFO - TIER STATUS - Drums and Drams: MICROBATCHES -> available | URL: https://www.patreon.com/c/drumsanddrams/membership
```

### Check Cycle
```
2025-08-11 17:30:15 - INFO - CHECK CYCLE #42 - Monitoring 3 creators, Interval: 600s
```

### Configuration Reload
```
2025-08-11 17:30:15 - INFO - CONFIG RELOADED - patreon_tier_alerter/config/config.json | Changes: creators: 4, interval: 300s, dev_mode: true
```

## 🎯 Benefits

1. **📈 Complete History**: All SMS alerts and bot activity are permanently recorded
2. **🔍 Easy Debugging**: Detailed logs for troubleshooting issues
3. **📊 Analytics**: Track tier availability patterns and alert frequency
4. **💾 Storage Management**: Automatic log rotation prevents disk space issues
5. **📱 SMS Tracking**: Dedicated log for all SMS alert history
6. **⚡ Hot-Reload Logging**: Configuration changes are logged with details

## 🚨 Troubleshooting

### Logs Not Appearing
- Check if `logs/` directory exists
- Verify bot has write permissions
- Check disk space availability

### Rotation Issues
- Verify logrotate is installed: `sudo apt install logrotate`
- Check logrotate configuration: `sudo logrotate -d /etc/logrotate.d/patreon-bot`
- Check system logs: `sudo journalctl -u logrotate`

### Permission Issues
- Ensure bot user owns log files: `sudo chown ubuntu:ubuntu logs/*.log`
- Check directory permissions: `ls -la logs/`
