#!/bin/bash
# Quick Production Test Script for Follow-Up Email System
# Usage: ./test_production_quick.sh [BASE_URL] [ADMIN_TOKEN]

set -e

# Configuration
BASE_URL=${1:-"http://localhost:8000"}
ADMIN_TOKEN=${2:-""}

echo "=========================================="
echo "QUICK PRODUCTION TEST - FOLLOW-UP SYSTEM"
echo "=========================================="
echo "Testing: $BASE_URL"
echo "Admin token: ${ADMIN_TOKEN:+[PROVIDED]}"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local expected_status="$4"
    local headers="$5"
    
    echo -n "Testing $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -o /tmp/response.json $headers "$url")
    else
        response=$(curl -s -w "%{http_code}" -o /tmp/response.json -X "$method" $headers "$url")
    fi
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code)"
        if [ -f /tmp/response.json ]; then
            echo "  Response: $(cat /tmp/response.json | head -c 100)..."
        fi
    else
        echo -e "${RED}❌ FAIL${NC} (HTTP $http_code, expected $expected_status)"
        if [ -f /tmp/response.json ]; then
            echo "  Response: $(cat /tmp/response.json)"
        fi
    fi
    echo ""
}

# Test 1: Basic health check
echo "1. BASIC HEALTH CHECK"
test_endpoint "Health endpoint" "GET" "$BASE_URL/api/v1/health" "200"

# Test 2: Database health (if available)
echo "2. DATABASE HEALTH"
test_endpoint "Database health" "GET" "$BASE_URL/api/v1/health/database" "200"

# Test 3: Email service status (requires admin token)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "3. EMAIL SERVICE STATUS"
    test_endpoint "Email service status" "GET" "$BASE_URL/api/v1/admin/email/status" "200" "-H \"Authorization: Bearer $ADMIN_TOKEN\""
else
    echo "3. EMAIL SERVICE STATUS - ${YELLOW}SKIPPED${NC} (no admin token)"
fi

# Test 4: Scheduler status (requires admin token)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "4. SCHEDULER STATUS"
    test_endpoint "Scheduler status" "GET" "$BASE_URL/api/v1/admin/scheduler/status" "200" "-H \"Authorization: Bearer $ADMIN_TOKEN\""
else
    echo "4. SCHEDULER STATUS - ${YELLOW}SKIPPED${NC} (no admin token)"
fi

# Test 5: Follow-up stats (requires admin token)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "5. FOLLOW-UP STATISTICS"
    test_endpoint "Follow-up stats" "GET" "$BASE_URL/api/v1/admin/access-request-follow-ups/stats" "200" "-H \"Authorization: Bearer $ADMIN_TOKEN\""
else
    echo "5. FOLLOW-UP STATISTICS - ${YELLOW}SKIPPED${NC} (no admin token)"
fi

# Test 6: Pending follow-ups (requires admin token)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "6. PENDING FOLLOW-UPS"
    test_endpoint "Pending follow-ups" "GET" "$BASE_URL/api/v1/admin/access-request-follow-ups/pending" "200" "-H \"Authorization: Bearer $ADMIN_TOKEN\""
else
    echo "6. PENDING FOLLOW-UPS - ${YELLOW}SKIPPED${NC} (no admin token)"
fi

# Test 7: Manual processing trigger (requires admin token)
if [ -n "$ADMIN_TOKEN" ]; then
    echo "7. MANUAL PROCESSING TRIGGER"
    test_endpoint "Manual processing" "POST" "$BASE_URL/api/v1/admin/access-request-follow-ups/process-pending" "200" "-H \"Authorization: Bearer $ADMIN_TOKEN\""
else
    echo "7. MANUAL PROCESSING TRIGGER - ${YELLOW}SKIPPED${NC} (no admin token)"
fi

echo "=========================================="
echo "QUICK TEST COMPLETE"
echo "=========================================="
echo ""
echo "For comprehensive testing, run:"
echo "  uv run python test_production_follow_up_system.py $BASE_URL $ADMIN_TOKEN"
echo ""
echo "For health monitoring, run:"
echo "  uv run python health_check_follow_up_system.py $BASE_URL $ADMIN_TOKEN"
echo ""
echo "For manual testing steps, see:"
echo "  PRODUCTION_TESTING_GUIDE.md"
