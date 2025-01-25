import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from research_agent.tracers import QueryTrace
from utils.token_tracking import TokenUsageTracker

def update_token_stats(trace: QueryTrace, prompt_tokens: int, completion_tokens: int,
                      model: str, prompt_id: Optional[str] = None) -> None:
    try:
        if not hasattr(trace, 'token_tracker'):
            trace.token_tracker = TokenUsageTracker()
            
        trace.add_token_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, 
            model_name=model,
            prompt_id=prompt_id
        )
        
        print("DEBUG: Updated token usage stats:")
        print(json.dumps(trace.token_tracker.get_usage_stats(), indent=2))
    except Exception:
        pass

def get_token_usage(trace: QueryTrace) -> Dict[str, Any]:
    if hasattr(trace, 'token_tracker'):
        token_stats = trace.token_tracker.get_usage_stats()
        
        print(f"DEBUG: Getting token usage for trace {trace.trace_id}")
        print(json.dumps(token_stats, indent=2))
        
        return token_stats
        
    return {
        'total_usage': {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        },
        'usage_by_model': {},
        'usage_by_prompt': {},
        'usage_timeline': []
    }

def load_research_history() -> List[QueryTrace]:
    try:
        traces_file = 'research_traces.jsonl'
        if not os.path.exists(traces_file):
            return []
            
        traces = []
        with open(traces_file, 'r') as f:
            for line in f:
                try:
                    trace_data = json.loads(line)
                    trace = QueryTrace(trace_data.get('query', 'Unknown'))
                    trace.data = trace_data
                    
                    token_usage = trace_data.get('token_usage', {})
                    if token_usage:
                        trace.token_tracker.usage_stats = token_usage
                        
                    traces.append(trace)
                except json.JSONDecodeError:
                    continue
                    
        return traces
    except Exception:
        return []