from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import json, boto3, os, subprocess, logging
from pathlib import Path
from datetime import datetime
from tools import GeneralAgent
from research_components.research import run_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

DATA_PATH = "/data"
RESEARCH_PATH = f"{DATA_PATH}/research"
REPORTS_PATH = f"{DATA_PATH}/reports"
R_SCRIPT_PATH = "/app/r_service/report.Rmd"
S3_BUCKET = os.getenv("AWS_BUCKET")

class ResearchRequest(BaseModel):
    query: str
    tool_name: Optional[str] = "General Agent"
    species: str

@app.get("/")
async def root():
    return {"message": "Research API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/research/")
async def perform_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    try:
        logger.info(f"Starting research for query: {request.query}")
        tool = GeneralAgent(include_summary=True)
        result, trace = run_tool(
            tool_name=request.tool_name,
            query=request.query,
            tool=tool
        )

        if result:
            output_data = {
                "summary": result.summary,
                "content": [{"title": item.title, "url": item.url, "snippet": item.snippet, "content": item.content} for item in result.content],
                "trace_data": trace.data,
                "species": request.species
            }

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(RESEARCH_PATH) / f"research_{timestamp}.json"
            Path(RESEARCH_PATH).mkdir(parents=True, exist_ok=True)
            Path(REPORTS_PATH).mkdir(parents=True, exist_ok=True)

            logger.info(f"Saving research results to {filepath}")
            with open(filepath, 'w') as f:
                json.dump(output_data, f)

            background_tasks.add_task(generate_report, request.species)
            return {"status": "success", "file_path": str(filepath)}

        raise HTTPException(status_code=400, detail="Research failed")
    except Exception as e:
        logger.error(f"Research failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def generate_report(species: str):
    try:
        logger.info(f"Starting report generation for species: {species}")
        latest_research = max(Path(RESEARCH_PATH).glob("research_*.json"), key=os.path.getctime)
        
        if not os.path.exists(R_SCRIPT_PATH):
            raise Exception(f"R script not found at {R_SCRIPT_PATH}")
        
        cmd = [
            "Rscript", "-e",
            f"rmarkdown::render('{R_SCRIPT_PATH}', params = list(species = '{species}'), output_file = '{REPORTS_PATH}/{species}.html')"
        ]
        
        env = {
            **os.environ,
            "R_SCRIPT_PATH": R_SCRIPT_PATH,
            "HOME": "/root",
            "PANDOC_DIR": "/root/.pandoc",
            "R_LIBS_USER": "/root/.R",
            "R_LIBS": "/usr/local/lib/R/site-library:/usr/lib/R/site-library:/usr/lib/R/library"
        }
        
        logger.info(f"Rendering report for species: {species}")
        logger.info(f"R Script Path: {R_SCRIPT_PATH}")
        logger.info(f"Reports Path: {REPORTS_PATH}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=REPORTS_PATH
        )
        
        logger.info("STDOUT: %s", result.stdout)
        logger.error("STDERR: %s", result.stderr)
        
        if result.returncode == 0:
            s3 = boto3.client('s3')
            report_path = f"{REPORTS_PATH}/{species}.html"
            s3_key = f"reports/{species}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            if not os.path.exists(report_path):
                raise Exception(f"Report file not found: {report_path}")
            
            logger.info(f"Uploading report to S3: {s3_key}")
            s3.upload_file(report_path, S3_BUCKET, s3_key)
            url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
            
            logger.info(f"Report successfully generated and uploaded: {url}")
            return {"status": "success", "report_url": url}
        
        raise Exception(f"R script failed with return code {result.returncode}. STDERR: {result.stderr}")
    
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}", exc_info=True)
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)