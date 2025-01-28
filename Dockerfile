# syntax=docker/dockerfile:1.4

# Stage 1: Build stage with full dependencies
FROM python:3.11-slim AS builder

# Enable BuildKit cache mount for apt
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    unzip \
    cython3 \
    python3-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    libatlas-base-dev \
    r-base \
    r-base-dev \
    pandoc \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libgeos-dev \
    libudunits2-dev \
    libproj-dev \
    libgdal-dev \
    default-jdk \
    libnode-dev \
    libmagick++-dev

# Set up R and Python environment
ENV R_HOME=/usr/lib/R \
    R_LIBS_USER=/root/.R \
    HOME=/root \
    PATH="/usr/lib/R/bin:/usr/lib/R/bin/R:/usr/bin:/usr/local/bin:${PATH}"

# Create necessary directories and verify R installation
RUN mkdir -p /root/.R && chmod -R 777 /root/.R && \
    which R && R --version && \
    which Rscript && Rscript --version

# Install R packages with cache mount
RUN --mount=type=cache,target=/root/.R/cache \
    Rscript -e 'install.packages(c( \
    "rmarkdown", \
    "evaluate", \
    "knitr", \
    "dplyr", \
    "ggplot2", \
    "dbplyr", \
    "DBI", \
    "DT", \
    "padr", \
    "plotly", \
    "duckdb", \
    "reactable", \
    "igraph", \
    "visNetwork", \
    "networkD3", \
    "maps", \
    "RColorBrewer", \
    "stringr", \
    "glue", \
    "tidyr", \
    "tinytex", \
    "htmltools", \
    "markdown", \
    "shiny"), \
    repos="https://cloud.r-project.org/", \
    dependencies=TRUE, \
    Ncpus = parallel::detectCores())'

# Install TinyTeX for PDF rendering
RUN Rscript -e 'tinytex::install_tinytex()'

# Install Python requirements
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Lightweight runtime image
FROM python:3.11-slim

# Install runtime dependencies with BuildKit cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    r-base \
    r-base-dev \
    pandoc \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libgeos-dev \
    libudunits2-dev \
    libproj-dev \
    libgdal-dev \
    default-jdk \
    libnode-dev \
    libmagick++-dev \
    chromium \
    chromium-driver \
    sqlite3 \
    netcat-traditional

# Create R library directory
RUN mkdir -p /usr/local/lib/R/site-library && \
    chmod -R 777 /usr/local/lib/R/site-library

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy R installation and packages
COPY --from=builder /usr/lib/R /usr/lib/R
COPY --from=builder /root/.R /root/.R
COPY --from=builder /root/.TinyTeX /root/.TinyTeX
COPY --from=builder /usr/local/lib/R/site-library /usr/local/lib/R/site-library

# Set environment variables
ENV R_HOME=/usr/lib/R \
    R_LIBS_USER=/root/.R \
    R_LIBS=/usr/local/lib/R/site-library:/usr/lib/R/site-library:/usr/lib/R/library \
    PATH="/usr/lib/R/bin:/usr/lib/R/bin/R:/usr/bin:/usr/local/bin:/root/.TinyTeX/bin/x86_64-linux:${PATH}" \
    HOME=/root \
    PANDOC_DIR=/root/.pandoc

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Install R packages in the final stage to ensure they're properly installed
RUN R -e 'install.packages(c("evaluate", "rmarkdown", "knitr", "yaml", "xfun", "jsonlite"), repos="https://cloud.r-project.org/", dependencies=TRUE)'

# Verify R installation and packages
RUN R -e 'library(evaluate); library(rmarkdown); library(dplyr); library(ggplot2); library(plotly)' && \
    which R && R --version && \
    which Rscript && Rscript --version

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000