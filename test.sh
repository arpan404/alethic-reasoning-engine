#!/bin/bash

# Test runner script for ARE (AI Recruitment Engine)
# Runs pytest with appropriate options and provides useful output

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default test target
TEST_TARGET="tests/unit/core/"
VERBOSE=""
COVERAGE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --all)
      TEST_TARGET="tests/"
      shift
      ;;
    --unit)
      TEST_TARGET="tests/unit/"
      shift
      ;;
    --core)
      TEST_TARGET="tests/unit/core/"
      shift
      ;;
    --integration)
      TEST_TARGET="tests/integration/"
      shift
      ;;
    --security)
      TEST_TARGET="tests/unit/core/test_security.py"
      shift
      ;;
    --auth)
      TEST_TARGET="tests/unit/core/test_authentication_middleware.py"
      shift
      ;;
    --authz)
      TEST_TARGET="tests/unit/core/test_authorization_middleware.py"
      shift
      ;;
    --rate-limit)
      TEST_TARGET="tests/unit/core/test_rate_limiting.py"
      shift
      ;;
    -v|--verbose)
      VERBOSE="-vv"
      shift
      ;;
    -c|--coverage)
      COVERAGE="--cov=. --cov-report=html --cov-report=term"
      shift
      ;;
    -h|--help)
      echo "Usage: ./test.sh [OPTIONS]"
      echo ""
      echo "Test targets:"
      echo "  --all              Run all tests (unit + integration)"
      echo "  --unit             Run all unit tests"
      echo "  --core             Run unit/core tests only (default)"
      echo "  --integration      Run integration tests only"
      echo "  --security         Run security tests only"
      echo "  --auth             Run authentication tests only"
      echo "  --authz            Run authorization tests only"
      echo "  --rate-limit       Run rate limiting tests only"
      echo ""
      echo "Options:"
      echo "  -v, --verbose      Verbose output"
      echo "  -c, --coverage     Generate coverage report (HTML + terminal)"
      echo "  -h, --help         Show this help message"
      echo ""
      echo "Examples:"
      echo "  ./test.sh                    # Run core tests (default)"
      echo "  ./test.sh --all              # Run all tests"
      echo "  ./test.sh --unit -v          # Run unit tests with verbose output"
      echo "  ./test.sh --security -c      # Run security tests with coverage"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Print header
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}ARE Test Runner${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Target: ${YELLOW}${TEST_TARGET}${NC}"
echo -e "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Run tests
echo -e "${BLUE}Running tests...${NC}"
echo ""

# Build the pytest command
CMD="uv run pytest ${TEST_TARGET} --tb=short -q ${VERBOSE} ${COVERAGE}"

if eval "$CMD"; then
  echo ""
  echo -e "${GREEN}✓ All tests passed!${NC}"
  echo ""
  
  # Show coverage report location if generated
  if [[ -n "$COVERAGE" ]]; then
    echo -e "${YELLOW}Coverage report generated at: htmlcov/index.html${NC}"
  fi
  
  exit 0
else
  echo ""
  echo -e "${RED}✗ Tests failed!${NC}"
  exit 1
fi
