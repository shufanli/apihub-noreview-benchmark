#!/bin/bash
# Deploy apihub-noreview to Tencent Cloud server via tccli TAT
# Strategy: git clone from GitHub, then docker build on the server
set -e

TENCENT_REGION=ap-hongkong
TENCENT_INSTANCE_ID=ins-5ee3ymo2
TCCLI=/Users/shufanli/Library/Python/3.9/bin/tccli

# Convert SSH URL to HTTPS for server access
REPO_URL_RAW=$(git remote get-url origin)
REPO_URL=$(echo "$REPO_URL_RAW" | sed 's|git@github.com:|https://github.com/|' | sed 's|\.git$||').git
BRANCH=$(git branch --show-current)

echo "Repo: $REPO_URL, Branch: $BRANCH"

DEPLOY_SCRIPT=$(cat << 'REMOTE_EOF'
#!/bin/bash
set -e

DEPLOY_DIR="/home/work/apihub-noreview"
REPO_URL="__REPO_URL__"
BRANCH="__BRANCH__"
CONTAINER_NAME="apihubnoreview-app"

echo "=== Pulling code ==="
if [ -d "$DEPLOY_DIR/.git" ]; then
  cd "$DEPLOY_DIR"
  git fetch origin
  git reset --hard "origin/$BRANCH"
else
  git clone "$REPO_URL" "$DEPLOY_DIR"
  cd "$DEPLOY_DIR"
  git checkout "$BRANCH"
fi

echo "=== Building Docker image ==="
cd "$DEPLOY_DIR"
docker build -t $CONTAINER_NAME .
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo "=== Starting container ==="
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --network codepulse-survey_default \
  -v apihubnoreview-data:/app/data \
  -e DATABASE_PATH=/app/data/apihub.db \
  -e FRONTEND_URL=https://teamocode.teamolab.com/apihubnoreview \
  --memory 512m \
  $CONTAINER_NAME

echo "=== Updating nginx ==="
NGINX_CONF=$(docker exec codepulse-survey-nginx-1 cat /etc/nginx/conf.d/default.conf)

if ! echo "$NGINX_CONF" | grep -q "location /apihubnoreview/"; then
  # Create nginx config snippet
  cat > /tmp/apihub-nginx.conf << 'NGINX_SNIPPET'
    location /apihubnoreview/_next/ {
        proxy_pass http://apihubnoreview-app:8080/apihubnoreview/_next/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /apihubnoreview/api/ {
        proxy_pass http://apihubnoreview-app:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /apihubnoreview/ {
        proxy_pass http://apihubnoreview-app:8080/apihubnoreview/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
NGINX_SNIPPET

  # Insert before the first location block
  docker cp /tmp/apihub-nginx.conf codepulse-survey-nginx-1:/tmp/apihub-nginx.conf
  docker exec codepulse-survey-nginx-1 sh -c "
    cp /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak
    sed -i '/location \/singleclaude\//r /tmp/apihub-nginx.conf' /etc/nginx/conf.d/default.conf
  "
  docker exec codepulse-survey-nginx-1 nginx -t && docker exec codepulse-survey-nginx-1 nginx -s reload
  echo "Nginx updated and reloaded"
else
  docker exec codepulse-survey-nginx-1 nginx -s reload
  echo "Nginx already configured, reloaded"
fi

echo "=== Waiting for services ==="
sleep 5
echo "Container status:"
docker ps | grep $CONTAINER_NAME
echo "=== Deploy complete ==="
REMOTE_EOF
)

# Replace placeholders
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//__REPO_URL__/$REPO_URL}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//__BRANCH__/$BRANCH}"

echo "=== Executing deploy on server via TAT ==="
INVOCATION_ID=$($TCCLI tat RunCommand \
  --region "$TENCENT_REGION" \
  --Content "$(echo "$DEPLOY_SCRIPT" | base64)" \
  --CommandType "SHELL" \
  --InstanceIds "[\"$TENCENT_INSTANCE_ID\"]" \
  --Timeout 600 \
  --Username "root" \
  --WorkingDirectory "/root" \
  2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['InvocationId'])")

echo "Invocation ID: $INVOCATION_ID"

# Wait for completion
for i in $(seq 1 60); do
  sleep 10
  STATUS=$($TCCLI tat DescribeInvocations \
    --region "$TENCENT_REGION" \
    --InvocationIds "[\"$INVOCATION_ID\"]" \
    2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['InvocationSet'][0]['InvocationStatus'])
" 2>/dev/null || echo "UNKNOWN")

  echo "[$i/60] Status: $STATUS"

  if [ "$STATUS" = "SUCCESS" ]; then
    echo "=== Deploy succeeded! ==="
    $TCCLI tat DescribeInvocationTasks \
      --region "$TENCENT_REGION" \
      --Filters "[{\"Name\":\"invocation-id\",\"Values\":[\"$INVOCATION_ID\"]}]" \
      2>/dev/null | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
for task in data.get('InvocationTaskSet', []):
    output = base64.b64decode(task.get('TaskResult', {}).get('Output', '')).decode('utf-8', errors='replace')
    print(output)
" 2>/dev/null || true
    break
  elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "TIMEOUT" ]; then
    echo "=== Deploy failed: $STATUS ==="
    $TCCLI tat DescribeInvocationTasks \
      --region "$TENCENT_REGION" \
      --Filters "[{\"Name\":\"invocation-id\",\"Values\":[\"$INVOCATION_ID\"]}]" \
      2>/dev/null | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
for task in data.get('InvocationTaskSet', []):
    output = base64.b64decode(task.get('TaskResult', {}).get('Output', '')).decode('utf-8', errors='replace')
    err = base64.b64decode(task.get('TaskResult', {}).get('Error', '')).decode('utf-8', errors='replace')
    print('STDOUT:', output)
    if err: print('STDERR:', err)
" 2>/dev/null || true
    exit 1
  fi
done

echo ""
echo "URL: https://teamocode.teamolab.com/apihubnoreview"
