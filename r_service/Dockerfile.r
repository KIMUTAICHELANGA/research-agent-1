FROM rocker/tidyverse:latest

RUN R -e "install.packages(c('rmarkdown', 'plotly', 'DT', 'visNetwork', 'duckdb', 'reactable', 'igraph', 'networkD3'))"

WORKDIR /app

COPY report.Rmd /app/