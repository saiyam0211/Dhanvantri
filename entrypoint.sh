#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧬 Pharmacogenomics Model Docker Container${NC}"
echo -e "${BLUE}==========================================${NC}"

# Function to log with timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check and download SnpEff database if needed
setup_snpeff_database() {
    log "${YELLOW}🔍 Checking SnpEff database...${NC}"
    
    # Store current directory
    ORIGINAL_DIR=$(pwd)
    
    if [ ! -f "${SNPEFF_HOME}/data/hg38/snpEffectPredictor.bin" ]; then
        log "${YELLOW}📥 SnpEff database not found. Downloading hg38 database...${NC}"
        log "${YELLOW}⏳ This may take several minutes...${NC}"
        
        cd ${SNPEFF_HOME}
        
        # Try to download database with retries
        for attempt in 1 2 3; do
            log "${BLUE}📥 Attempt $attempt of 3 to download SnpEff database${NC}"
            if java -jar snpEff.jar download hg38; then
                log "${GREEN}✅ SnpEff database downloaded successfully${NC}"
                break
            else
                log "${RED}❌ Database download attempt $attempt failed${NC}"
                if [ $attempt -lt 3 ]; then
                    log "${YELLOW}⏳ Retrying in 10 seconds...${NC}"
                    sleep 10
                else
                    log "${RED}❌ Failed to download SnpEff database after 3 attempts${NC}"
                    log "${YELLOW}⚠ Continuing without annotation - VCF should be pre-annotated${NC}"
                fi
            fi
        done
    else
        log "${GREEN}✅ SnpEff database already available${NC}"
    fi
    
    # Always return to original directory
    cd "$ORIGINAL_DIR"
}

# Ensure we start in the correct directory
cd /app

log "${BLUE}🚀 Starting Pharmacogenomics Analysis...${NC}"

# Handle help command
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    python3 main.py --help
    exit 0
fi

# Check if VCF file is provided and exists
VCF_FILE=""
DRUGS=""
OUTPUT_FILE=""
PATIENT_ID=""
VERBOSE=""
NO_COHERE=""

# Parse arguments to extract VCF file for validation
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
    case "${args[i]}" in
        --vcf)
            if [ $((i+1)) -lt ${#args[@]} ]; then
                VCF_FILE="${args[$((i+1))]}"
            fi
            ;;
        --drugs)
            if [ $((i+1)) -lt ${#args[@]} ]; then
                DRUGS="${args[$((i+1))]}"
            fi
            ;;
        --output)
            if [ $((i+1)) -lt ${#args[@]} ]; then
                OUTPUT_FILE="${args[$((i+1))]}"
            fi
            ;;
        --patient-id)
            if [ $((i+1)) -lt ${#args[@]} ]; then
                PATIENT_ID="${args[$((i+1))]}"
            fi
            ;;
        --verbose)
            VERBOSE="--verbose"
            ;;
        --no-cohere)
            NO_COHERE="--no-cohere"
            ;;
    esac
done

# Validate VCF file exists
if [ -n "$VCF_FILE" ]; then
    if [ -f "$VCF_FILE" ]; then
        log "${GREEN}✅ VCF file found: $VCF_FILE${NC}"
    else
        log "${RED}❌ VCF file not found: $VCF_FILE${NC}"
        exit 1
    fi
fi

if [ -n "$DRUGS" ]; then
    log "${GREEN}✅ Drugs specified: $DRUGS${NC}"
fi

if [ -f "/app/api_keys.json" ]; then
    log "${GREEN}✅ API keys file found${NC}"
else
    log "${YELLOW}⚠ API keys file not found - some features may be limited${NC}"
fi

# Setup SnpEff database if annotation is needed (but don't fail if it doesn't work)
if [[ "$" != *"--no-annotation" ]]; then
    setup_snpeff_database || true
else
    log "${YELLOW}⚠ Annotation disabled via --no-annotation flag${NC}"
fi

# Ensure we're in the correct directory before executing
cd /app
log "${BLUE}Current directory: $(pwd)${NC}"
log "${GREEN}🧬 Executing pharmacogenomics analysis...${NC}"
log "${BLUE}Command: python3 main.py $*${NC}"

# Verify main.py exists
if [ ! -f "main.py" ]; then
    log "${RED}❌ main.py not found in $(pwd)${NC}"
    log "${RED}Directory contents:${NC}"
    ls -la
    exit 1
fi

# Execute the main application
exec python3 main.py "$@"
