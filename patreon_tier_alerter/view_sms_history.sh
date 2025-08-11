#!/bin/bash

# SMS Alert History Viewer for Patreon Tier Alerter Bot
# Usage: ./view_sms_history.sh [option]

LOG_DIR="logs"
SMS_LOG="$LOG_DIR/sms_alerts.log"

echo "📱 Patreon Bot SMS Alert History Viewer"
echo "======================================"

if [ ! -f "$SMS_LOG" ]; then
    echo "❌ SMS alerts log not found: $SMS_LOG"
    exit 1
fi

case "${1:-all}" in
    "sent")
        echo "✅ SMS Alerts Sent:"
        echo "=================="
        grep "SMS ALERT SENT" "$SMS_LOG" | tail -10
        ;;
    "failed")
        echo "❌ SMS Alerts Failed:"
        echo "===================="
        grep "SMS ALERT FAILED" "$SMS_LOG" | tail -10
        ;;
    "tiers")
        echo "🎯 Tier Status Changes:"
        echo "======================"
        grep "TIER STATUS" "$SMS_LOG" | tail -10
        ;;
    "count")
        echo "📊 SMS Alert Statistics:"
        echo "======================="
        total_sent=$(grep "SMS ALERT SENT" "$SMS_LOG" | wc -l)
        total_failed=$(grep "SMS ALERT FAILED" "$SMS_LOG" | wc -l)
        echo "Total SMS Alerts Sent: $total_sent"
        echo "Total SMS Alerts Failed: $total_failed"
        echo "Total Tier Status Changes: $(grep "TIER STATUS" "$SMS_LOG" | wc -l)"
        ;;
    "recent")
        echo "🕒 Recent SMS Activity (Last 20 entries):"
        echo "======================================="
        tail -20 "$SMS_LOG"
        ;;
    "all"|*)
        echo "📋 All SMS Alert History:"
        echo "========================"
        cat "$SMS_LOG"
        ;;
esac

echo ""
echo "💡 Usage: $0 [sent|failed|tiers|count|recent|all]"
echo "   sent   - Show last 10 successful SMS alerts"
echo "   failed - Show last 10 failed SMS alerts"
echo "   tiers  - Show last 10 tier status changes"
echo "   count  - Show SMS alert statistics"
echo "   recent - Show last 20 log entries"
echo "   all    - Show complete SMS alert history (default)"
