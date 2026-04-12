#!/usr/bin/env bash
set -euo pipefail

mkdir -p logs

# Generate app.log with 5000 lines of realistic application log entries
{
    for i in $(seq 1 5000); do
        ts=$(printf "2026-03-20 %02d:%02d:%02d" $((i % 24)) $((i % 60)) $((i % 60)))
        case $((i % 5)) in
            0) level="ERROR"; msg="Connection timeout to database pool (attempt $i)";;
            1) level="INFO";  msg="Request processed successfully id=$i duration=${i}ms";;
            2) level="WARN";  msg="Memory usage at $((50 + i % 45))% threshold";;
            3) level="DEBUG"; msg="Cache lookup for key=user:$i result=HIT";;
            4) level="INFO";  msg="Health check passed uptime=$((i * 60))s";;
        esac
        echo "[$ts] $level $msg"
    done
} > logs/app.log

# Generate access.log with 3000 lines of HTTP access log entries
{
    for i in $(seq 1 3000); do
        ip="192.168.$((i % 256)).$((i % 256))"
        ts=$(printf "20/Mar/2026:%02d:%02d:%02d +0000" $((i % 24)) $((i % 60)) $((i % 60)))
        case $((i % 4)) in
            0) method="GET";  path="/api/users/$i"; status=200; size=$((500 + i));;
            1) method="POST"; path="/api/orders"; status=201; size=$((1000 + i));;
            2) method="GET";  path="/health"; status=200; size=23;;
            3) method="GET";  path="/api/products/$((i % 100))"; status=$((200 + (i % 3) * 100)); size=$((200 + i));;
        esac
        echo "$ip - - [$ts] \"$method $path HTTP/1.1\" $status $size"
    done
} > logs/access.log

# Create pre-existing rotated logs (older data)
{
    for i in $(seq 1 2000); do
        ts=$(printf "2026-03-19 %02d:%02d:%02d" $((i % 24)) $((i % 60)) $((i % 60)))
        echo "[$ts] INFO Old app entry $i — this is from the previous rotation"
    done
} | gzip > logs/app.log.1.gz

{
    for i in $(seq 1 1500); do
        ip="10.0.$((i % 256)).$((i % 256))"
        ts=$(printf "19/Mar/2026:%02d:%02d:%02d +0000" $((i % 24)) $((i % 60)) $((i % 60)))
        echo "$ip - - [$ts] \"GET /old/path/$i HTTP/1.1\" 200 $((100 + i))"
    done
} | gzip > logs/access.log.1.gz

echo "Setup complete. logs/ has app.log (5000 lines), access.log (3000 lines), and pre-existing .1.gz rotations."
