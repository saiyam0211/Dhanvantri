# Use Python 3.11 slim as base image for better compatibility
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV FLASK_ENV=production
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DEBUG=false

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    libz-dev \
    libbz2-dev \
    liblzma-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    tabix \
    bcftools \
    samtools \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs logs data

# Download and setup reference data
RUN mkdir -p data/reference && \
    cd data/reference && \
    wget -q https://ftp.ncbi.nlm.nih.gov/snp/organisms/human_9606_b151_GRCh38p7/VCF/common_all_20180418.vcf.gz && \
    wget -q https://ftp.ncbi.nlm.nih.gov/snp/organisms/human_9606_b151_GRCh38p7/VCF/common_all_20180418.vcf.gz.tbi

# Set permissions
RUN chmod +x main.py && \
    chmod -R 755 uploads outputs logs data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Add labels for better container management
LABEL maintainer="Pharmacogenomics Team"
LABEL version="2.0"
LABEL description="Streamlined Pharmacogenomics Analysis with SnpEff annotation and Cohere AI"

# Run the Flask application
CMD ["python", "app.py"]
