#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

IMAGE_NAME="pharmacogenomics-model"
IMAGE_TAG="latest"
CONTAINER_NAME="pharmacogenomics-analysis"

usage() {
    echo -e "${BLUE}Pharmacogenomics Model Docker Runner${NC}"
    echo -e "${BLUE}====================================${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build                 Build the Docker image"
    echo "  run                   Run analysis with your parameters"
    echo "  example               Run with example data"
    echo "  shell                 Open shell in container for debugging"
    echo "  clean                 Remove container and image"
    echo "  help                  Show this help message"
    echo ""
    echo "Run Options (use with 'run' command):"
    echo "  --vcf-dir PATH        Directory containing VCF files (required)"
    echo "  --output-dir PATH     Directory for output reports (required)"
    echo "  --api-keys PATH       Path to api_keys.json file"
    echo "  --vcf-file NAME       VCF filename (inside vcf-dir)"
    echo "  --drugs DRUGS         Comma-separated drug list"
    echo "  --patient-id ID       Patient identifier"
    echo "  --memory SIZE         Memory limit (e.g., 8g, 16g)"
    echo "  --cpus NUM            Number of CPU cores"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run --vcf-dir ./samples --output-dir ./output --vcf-file HG00098.anno.vcf --drugs 'Warfarin,Simvastatin' --patient-id HG00098"
    echo "  $0 example"
    echo "  $0 shell"
    echo ""
}

build_image() {
    echo -e "${BLUE} Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    
    if [ ! -f "Dockerfile" ]; then
        echo -e "${RED} Dockerfile not found in current directory${NC}"
        exit 1
    fi
    
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Docker image built successfully${NC}"
        echo -e "${GREEN}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    else
        echo -e "${RED}❌ Failed to build Docker image${NC}"
        exit 1
    fi
}

run_analysis() {
    local vcf_dir=""
    local output_dir=""
    local api_keys=""
    local vcf_file=""
    local drugs=""
    local patient_id=""
    local memory="8g"
    local cpus="4"
    local extra_args=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --vcf-dir)
                vcf_dir="$2"
                shift 2
                ;;
            --output-dir)
                output_dir="$2"
                shift 2
                ;;
            --api-keys)
                api_keys="$2"
                shift 2
                ;;
            --vcf-file)
                vcf_file="$2"
                shift 2
                ;;
            --drugs)
                drugs="$2"
                shift 2
                ;;
            --patient-id)
                patient_id="$2"
                shift 2
                ;;
            --memory)
                memory="$2"
                shift 2
                ;;
            --cpus)
                cpus="$2"
                shift 2
                ;;
            *)
                extra_args="$extra_args $1"
                shift
                ;;
        esac
    done
    

    if [ -z "$vcf_dir" ] || [ -z "$output_dir" ]; then
        echo -e "${RED} Error: --vcf-dir and --output-dir are required${NC}"
        echo ""
        usage
        exit 1
    fi
    

    if [ ! -d "$vcf_dir" ]; then
        echo -e "${RED} VCF directory not found: $vcf_dir${NC}"
        exit 1
    fi
    

    mkdir -p "$output_dir"
    
    # Build Docker run command
    docker_cmd="docker run -it --rm"
    docker_cmd="$docker_cmd --name $CONTAINER_NAME"
    docker_cmd="$docker_cmd --memory=$memory"
    docker_cmd="$docker_cmd --cpus=$cpus"
    docker_cmd="$docker_cmd -v $(realpath $vcf_dir):/app/samples"
    docker_cmd="$docker_cmd -v $(realpath $output_dir):/app/output"
    

    if [ -n "$api_keys" ] && [ -f "$api_keys" ]; then
        docker_cmd="$docker_cmd -v $(realpath $api_keys):/app/api_keys.json"
        echo -e "${GREEN} API keys file mounted${NC}"
    else
        echo -e "${YELLOW} No API keys provided. Some AI features may be limited.${NC}"
    fi
    

    docker_cmd="$docker_cmd -e JAVA_OPTS='-Xmx$(echo $memory | sed 's/g//')g'"
    

    docker_cmd="$docker_cmd $IMAGE_NAME:$IMAGE_TAG"
    

    if [ -n "$vcf_file" ]; then
        docker_cmd="$docker_cmd --vcf samples/$vcf_file"
    fi
    
    if [ -n "$drugs" ]; then
        docker_cmd="$docker_cmd --drugs \"$drugs\""
    fi
    
    if [ -n "$patient_id" ]; then
        docker_cmd="$docker_cmd --patient-id \"$patient_id\""
    fi
    

    docker_cmd="$docker_cmd --output output/report.html --verbose --no-biomedlm"
    

    if [ -n "$extra_args" ]; then
        docker_cmd="$docker_cmd $extra_args"
    fi
    
    echo -e "${BLUE} Running pharmacogenomics analysis...${NC}"
    echo -e "${BLUE} VCF Directory: $vcf_dir${NC}"
    echo -e "${BLUE} Output Directory: $output_dir${NC}"
    echo -e "${BLUE} Memory: $memory${NC}"
    echo -e "${BLUE} CPUs: $cpus${NC}"
    echo ""
    echo -e "${YELLOW}Command: $docker_cmd${NC}"
    echo ""
    

    eval $docker_cmd
}


run_example() {
    echo -e "${BLUE} Running example analysis...${NC}"
    

    if [ ! -d "samples" ]; then
        echo -e "${YELLOW} Creating samples directory...${NC}"
        mkdir -p samples
    fi
    
    if [ ! -d "output" ]; then
        echo -e "${YELLOW} Creating output directory...${NC}"
        mkdir -p output
    fi
    
    # Check for VCF file
    vcf_file=""
    if [ -f "samples/HG00098.anno.vcf" ]; then
        vcf_file="HG00098.anno.vcf"
    elif [ -f "samples/test.vcf" ]; then
        vcf_file="test.vcf"
    else
        # Find any VCF file
        vcf_file=$(find samples -name "*.vcf" | head -1 | xargs basename 2>/dev/null || echo "")
    fi
    
    if [ -z "$vcf_file" ]; then
        echo -e "${RED} No VCF files found in samples directory${NC}"
        echo -e "${YELLOW} Please add a VCF file to the samples directory${NC}"
        exit 1
    fi
    
    echo -e "${GREEN} Found VCF file: $vcf_file${NC}"
    
    # Run example analysis
    run_analysis \
        --vcf-dir ./samples \
        --output-dir ./output \
        --vcf-file "$vcf_file" \
        --drugs "Warfarin,Simvastatin,Omeprazole" \
        --patient-id "EXAMPLE_001" \
        --memory 8g \
        --cpus 4
}

# Function to open shell in container
open_shell() {
    echo -e "${BLUE} Opening shell in container...${NC}"
    
    docker run -it --rm \
        --name "${CONTAINER_NAME}-shell" \
        -v "$(pwd):/app/host" \
        "$IMAGE_NAME:$IMAGE_TAG" \
        bash
}

# Function to clean up
clean_up() {
    echo -e "${BLUE} Cleaning up Docker resources...${NC}"
    
    # Stop and remove container if running
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo -e "${YELLOW} Stopping running container...${NC}"
        docker stop "$CONTAINER_NAME"
    fi
    
    # Remove container if exists
    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        echo -e "${YELLOW} Removing container...${NC}"
        docker rm "$CONTAINER_NAME"
    fi
    
    # Remove image
    if docker images -q "$IMAGE_NAME:$IMAGE_TAG" | grep -q .; then
        echo -e "${YELLOW} Removing image...${NC}"
        docker rmi "$IMAGE_NAME:$IMAGE_TAG"
    fi
    
    echo -e "${GREEN} Cleanup completed${NC}"
}

# Main script logic
case "${1:-help}" in
    build)
        build_image
        ;;
    run)
        shift
        run_analysis "$@"
        ;;
    example)
        run_example
        ;;
    shell)
        open_shell
        ;;
    clean)
        clean_up
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo -e "${RED} Unknown command: $1${NC}"
        echo ""
        usage
        exit 1
        ;;
esac
