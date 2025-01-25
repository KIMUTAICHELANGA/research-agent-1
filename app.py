from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path
import boto3
import os
import subprocess
from datetime import datetime

app = FastAPI()

# Paths and configs
DATA_PATH = "/data"
RESEARCH_PATH = f"{DATA_PATH}/research"
REPORTS_PATH = f"{DATA_PATH}/reports"
R_SCRIPT_PATH = "/app/report.Rmd"
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
       tool = GeneralAgent(include_summary=True)
       result, trace = run_tool(
           tool_name=request.tool_name,
           query=request.query,
           tool=tool
       )

       if result:
           output_data = {
               "summary": result.summary,
               "content": [
                   {
                       "title": item.title,
                       "url": item.url,
                       "snippet": item.snippet,
                       "content": item.content
                   } for item in result.content
               ],
               "trace_data": trace.data,
               "species": request.species
           }

           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           filename = f"research_{timestamp}.json"
           filepath = Path(RESEARCH_PATH) / filename

           Path(RESEARCH_PATH).mkdir(parents=True, exist_ok=True)
           Path(REPORTS_PATH).mkdir(parents=True, exist_ok=True)

           with open(filepath, 'w') as f:
               json.dump(output_data, f)

           background_tasks.add_task(generate_report, request.species)
           
           return {
               "status": "success",
               "file_path": str(filepath)
           }

       raise HTTPException(status_code=400, detail="Research failed")

   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

async def generate_report(species: str):
   try:
       latest_research = max(Path(RESEARCH_PATH).glob("research_*.json"),
                           key=os.path.getctime)

       if not os.path.exists(R_SCRIPT_PATH):
           raise Exception(f"R script not found at {R_SCRIPT_PATH}")

       cmd = [
           "Rscript",
           "-e",
           f"""
           rmarkdown::render(
               '{R_SCRIPT_PATH}',
               params = list(
                   species = '{species}'
               ),
               output_file = '{REPORTS_PATH}/{species}.html'
           )
           """
       ]
       
       result = subprocess.run(
           cmd,
           capture_output=True,
           text=True,
           env={"R_SCRIPT_PATH": R_SCRIPT_PATH}
       )
       
       if result.returncode == 0:
           s3 = boto3.client('s3')
           report_path = f"{REPORTS_PATH}/{species}.html"
           s3_key = f"reports/{species}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
           
           s3.upload_file(report_path, S3_BUCKET, s3_key)
           url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
           
           return {"status": "success", "report_url": url}
           
       raise Exception(f"R script failed: {result.stderr}")

   except Exception as e:
       print(f"Report generation failed: {str(e)}")
       return None

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(app, host="0.0.0.0", port=8000)