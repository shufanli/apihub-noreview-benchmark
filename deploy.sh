#!/bin/bash
# Deploy apihub-noreview to Tencent Cloud server via tccli TAT
# Strategy: split archive into chunks, upload via multiple TAT commands, then assemble and deploy
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Tencent Cloud config
TENCENT_REGION=ap-hongkong
TENCENT_INSTANCE_ID=ins-5ee3ymo2
TCCLI=/Users/shufanli/Library/Python/3.9/bin/tccli

CONTAINER_NAME=apihubnoreview-app
DEPLOY_DIR=/home/work/apihub-noreview
NGINX_LOCATION="/apihubnoreview/"

run_tat() {
  local script_content="$1"
  local timeout="${2:-300}"
  local script_b64=$(echo "$script_content" | base64)

  local INVOCATION=$($TCCLI tat RunCommand \
    --region $TENCENT_REGION \
    --InstanceIds "[\"$TENCENT_INSTANCE_ID\"]" \
    --CommandType SHELL \
    --Timeout "$timeout" \
    --Content "$script_b64" 2>/dev/null)

  local INV_ID=$(echo "$INVOCATION" | python3 -c "import sys,json; print(json.load(sys.stdin)['InvocationId'])")
  echo "  Invocation: $INV_ID"

  for i in $(seq 1 60); do
    sleep 5
    local RESULT=$($TCCLI tat DescribeInvocations \
      --region $TENCENT_REGION \
      --InvocationIds "[\"$INV_ID\"]" 2>/dev/null)

    local STATUS=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['InvocationSet'][0]['InvocationStatus'])" 2>/dev/null)

    if [ "$STATUS" = "SUCCESS" ]; then
      echo "  OK"
      # Print output
      $TCCLI tat DescribeInvocationTasks \
        --region $TENCENT_REGION \
        --Filters "[{\"Name\": \"invocation-id\", \"Values\": [\"$INV_ID\"]}]" 2>/dev/null | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
for t in d.get('InvocationTaskSet', []):
    output = t.get('TaskResult', {}).get('Output', '')
    if output:
        try: print(base64.b64decode(output).decode())
        except: print(output)
" 2>/dev/null || true
      return 0
    elif [ "$STATUS" = "FAILED" ]; then
      echo "  FAILED"
      $TCCLI tat DescribeInvocationTasks \
        --region $TENCENT_REGION \
        --Filters "[{\"Name\": \"invocation-id\", \"Values\": [\"$INV_ID\"]}]" 2>/dev/null | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
for t in d.get('InvocationTaskSet', []):
    output = t.get('TaskResult', {}).get('Output', '')
    if output:
        try: print(base64.b64decode(output).decode())
        except: print(output)
" 2>/dev/null || true
      return 1
    fi
  done
  echo "  TIMEOUT"
  return 1
}

echo "=== Step 1: Pack project files ==="
cd "$SCRIPT_DIR"
tar czf /tmp/apihub-noreview.tar.gz \
  --exclude='.git' --exclude='.env.dev' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.claude' --exclude='prd' \
  --exclude='metrics.jsonl' --exclude='deploy.sh' --exclude='CLAUDE.md' \
  --exclude='.DS_Store' --exclude='backend/tests' \
  --exclude='frontend/node_modules' --exclude='frontend/.next' \
  --exclude='collect_metrics.py' --exclude='backend/apihub.db' \
  backend/ frontend/ Dockerfile start.sh

FILE_SIZE=$(ls -lh /tmp/apihub-noreview.tar.gz | awk '{print $5}')
echo "Package size: $FILE_SIZE"

echo "=== Step 2: Split and upload archive in chunks ==="
# Split into 100KB chunks
CHUNK_DIR=/tmp/apihub-chunks
rm -rf $CHUNK_DIR
mkdir -p $CHUNK_DIR
split -b 100k /tmp/apihub-noreview.tar.gz $CHUNK_DIR/chunk_

CHUNKS=($(ls $CHUNK_DIR/chunk_*))
echo "Total chunks: ${#CHUNKS[@]}"

# Clean remote staging area
echo "  Cleaning remote staging..."
run_tat "rm -rf /tmp/apihub-chunks && mkdir -p /tmp/apihub-chunks"

# Upload each chunk
for i in "${!CHUNKS[@]}"; do
  CHUNK_FILE=${CHUNKS[$i]}
  CHUNK_NAME=$(basename $CHUNK_FILE)
  CHUNK_B64=$(base64 < $CHUNK_FILE)
  echo "  Uploading chunk $((i+1))/${#CHUNKS[@]}: $CHUNK_NAME"

  run_tat "base64 -d <<'B64END' > /tmp/apihub-chunks/$CHUNK_NAME
$CHUNK_B64
B64END
echo 'Chunk $CHUNK_NAME uploaded ($(wc -c < /tmp/apihub-chunks/$CHUNK_NAME) bytes)'"
done

echo "=== Step 3: Assemble and deploy ==="
run_tat "#!/bin/bash
set -e

echo '=== Assembling archive ==='
cat /tmp/apihub-chunks/chunk_* > /tmp/apihub-noreview.tar.gz
ls -lh /tmp/apihub-noreview.tar.gz
rm -rf /tmp/apihub-chunks

echo '=== Extracting ==='
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR
tar xzf /tmp/apihub-noreview.tar.gz
rm -f /tmp/apihub-noreview.tar.gz

echo '=== Building Docker image ==='
docker build -t $CONTAINER_NAME .
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo '=== Starting container ==='
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --network codepulse-survey_default \
  -v apihubnoreview-data:/app/data \
  -e DATABASE_PATH=/app/data/apihub.db \
  -e FRONTEND_URL=https://teamocode.teamolab.com/apihubnoreview \
  --memory 512m \
  $CONTAINER_NAME

echo '=== Updating nginx ==='
NGINX_CONF=\$(docker exec codepulse-survey-nginx-1 cat /etc/nginx/conf.d/default.conf)

if ! echo \"\$NGINX_CONF\" | grep -q 'location ${NGINX_LOCATION}'; then
  docker exec codepulse-survey-nginx-1 sh -c \"
    cp /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
    sed -i '/location \/singleclaude\//i\\\\
    location ${NGINX_LOCATION} {\\\\n        proxy_pass http://${CONTAINER_NAME}:8080/apihubnoreview/;\\\\n        proxy_set_header Host \\\\\\\\\\\$host;\\\\n        proxy_set_header X-Real-IP \\\\\\\\\\\$remote_addr;\\\\n        proxy_set_header X-Forwarded-Proto \\\\\\\\\\\$scheme;\\\\n        proxy_set_header X-Forwarded-For \\\\\\\\\\\$proxy_add_x_forwarded_for;\\\\n    }\\\\n\\\\n    location /apihubnoreview/api/ {\\\\n        proxy_pass http://${CONTAINER_NAME}:8000/api/;\\\\n        proxy_set_header Host \\\\\\\\\\\$host;\\\\n        proxy_set_header X-Real-IP \\\\\\\\\\\$remote_addr;\\\\n        proxy_set_header X-Forwarded-Proto \\\\\\\\\\\$scheme;\\\\n        proxy_set_header X-Forwarded-For \\\\\\\\\\\$proxy_add_x_forwarded_for;\\\\n    }' /etc/nginx/conf.d/default.conf
  \"
  docker exec codepulse-survey-nginx-1 nginx -t && docker exec codepulse-survey-nginx-1 nginx -s reload
  echo 'Nginx updated and reloaded'
else
  docker exec codepulse-survey-nginx-1 nginx -s reload
  echo 'Nginx config already has ${NGINX_LOCATION}, reloaded'
fi

echo '=== Deploy complete ==='
docker ps | grep $CONTAINER_NAME
" 600

echo "=== Done ==="
echo "URL: https://teamocode.teamolab.com/apihubnoreview"
rm -rf $CHUNK_DIR /tmp/apihub-noreview.tar.gz
