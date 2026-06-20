#!/bin/bash
cd /home/mikt06/词达人
LAST=0; STABLE=0
echo "=== 开始 $(date) ==="
while true; do
    python3 cidaren.py --auto 2>&1 | tail -1
    SCORE=$(grep "总得分:" run.log | tail -1 | grep -oP '[0-9]{4,}')
    [ -z "$SCORE" ] && SCORE=$LAST
    if [ "$SCORE" = "$LAST" ]; then
        STABLE=$((STABLE+1))
        echo "[$(date '+%H:%M:%S')] $SCORE 未变($STABLE/3)"
        [ $STABLE -ge 3 ] && { echo "稳定! 最终: $SCORE"; break; }
    else
        STABLE=0
        echo "[$(date '+%H:%M:%S')] $LAST → $SCORE"
    fi
    LAST=$SCORE
    sleep 5
done
echo "===== DONE ====="
