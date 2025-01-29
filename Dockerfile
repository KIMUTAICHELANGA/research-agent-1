# Start with rocker/tidyverse as base image
FROM rocker/tidyverse:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libssl-dev \
    libcurl4-openssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA and install Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

# Install additional system dependencies for DuckDB
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV HOME=/root
ENV PANDOC_DIR=/root/.pandoc
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH="$VIRTUAL_ENV/lib/python3.11/site-packages:$PYTHONPATH"

# Create necessary directories
RUN mkdir -p /root/.pandoc
RUN mkdir -p /usr/local/lib/R/site-library
RUN mkdir -p /app

# Create and activate virtual environment with Python 3.11
RUN python3.11 -m venv $VIRTUAL_ENV

# Install pip in the virtual environment
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.11 get-pip.py && \
    rm get-pip.py

# Set working directory
WORKDIR /app

# Install R packages
RUN R -e "install.packages(c( \
    'dplyr', \
    'ggplot2', \
    'dbplyr', \
    'DBI', \
    'DT', \
    'padr', \
    'plotly', \
    'duckdb', \
    'reactable', \
    'igraph', \
    'visNetwork', \
    'networkD3', \
    'stringr', \
    'glue', \
    'maps', \
    'RColorBrewer', \
    'tidyr' \
    ), repos='https://cran.rstudio.com/')"

# Install Python packages in virtual environment
COPY requirements.txt /app/requirements.txt
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . /app/

# Set permissions
RUN chmod -R 755 /app

# Expose ports
EXPOSE 8787 8501 8000

# Set library path
ENV R_LIBS_USER=/usr/local/lib/R/site-library

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["R", "-q", "-e", "TRUE"]

# Default command
CMD ["R"]