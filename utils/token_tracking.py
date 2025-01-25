from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

@dataclass
class TokenUsageEntry:
   timestamp: str
   prompt_tokens: int
   completion_tokens: int
   model: str
   prompt_id: Optional[str] = None
   cost: float = 0.0
   total_tokens: int = 0 
   processing_time: float = 0.0
   processing_speed: float = 0.0

class TokenUsageTracker:
   _instance = None
   
   def __new__(cls):
       if cls._instance is None:
           cls._instance = super(TokenUsageTracker, cls).__new__(cls)
           cls._instance._initialized = False
       return cls._instance
   
   def __init__(self):
       if not self._initialized:
           self.instance_id = id(self)
           self._usage_timeline = []
           self._total_prompt_tokens = 0
           self._total_completion_tokens = 0
           self._total_tokens = 0
           self._model_usage = {}
           
           self._cost_rates = {
               'gpt-3.5-turbo': {'prompt': 0.0015, 'completion': 0.002},
               'gpt-4': {'prompt': 0.03, 'completion': 0.06},
               'gpt-4-turbo': {'prompt': 0.01, 'completion': 0.03},
               'claude-3-opus': {'prompt': 0.015, 'completion': 0.075},
               'claude-3-sonnet': {'prompt': 0.003, 'completion': 0.015},
               'llama3-70b-8192': {'prompt': 0.0007, 'completion': 0.0007}
           }
           self._initialized = True

   def _get_processing_time(self) -> float:
       return 0.5

   def add_usage(
       self,
       prompt_tokens: int,
       completion_tokens: int,
       model: str,
       prompt_id: Optional[str] = None
   ) -> None:
       try:
           cost = 0.0
           if model in self._cost_rates:
               rates = self._cost_rates[model]
               prompt_cost = (prompt_tokens / 1000) * rates['prompt']
               completion_cost = (completion_tokens / 1000) * rates['completion']
               cost = prompt_cost + completion_cost

           total_tokens = prompt_tokens + completion_tokens
           processing_time = self._get_processing_time()
           processing_speed = total_tokens / processing_time if processing_time > 0 else 0
           
           usage_entry = TokenUsageEntry(
               timestamp=datetime.now().isoformat(),
               prompt_tokens=prompt_tokens,
               completion_tokens=completion_tokens,
               model=model,
               prompt_id=prompt_id,
               cost=cost,
               total_tokens=total_tokens,
               processing_time=processing_time,
               processing_speed=processing_speed
           )
           
           self._usage_timeline.append(usage_entry)
           
           self._total_prompt_tokens += prompt_tokens
           self._total_completion_tokens += completion_tokens
           self._total_tokens += total_tokens

       except Exception as e:
           raise

   def get_usage_stats(self) -> Dict:
       try:
           if not self._usage_timeline:
               return {
                   'model': 'no_model',
                   'tokens': {
                       'input': 0,
                       'output': 0,
                       'total': 0
                   },
                   'processing': {
                       'time': 0,
                       'speed': 0
                   },
                   'cost': 0.0
               }
           
           total_prompt_tokens = sum(entry.prompt_tokens for entry in self._usage_timeline)
           total_completion_tokens = sum(entry.completion_tokens for entry in self._usage_timeline)
           total_tokens = total_prompt_tokens + total_completion_tokens
           total_cost = sum(entry.cost for entry in self._usage_timeline)
           total_time = sum(entry.processing_time for entry in self._usage_timeline)
           
           avg_speed = total_tokens / total_time if total_time > 0 else 0

           model_counts = {}
           for entry in self._usage_timeline:
               model_counts[entry.model] = model_counts.get(entry.model, 0) + 1
           
           most_used_model = max(model_counts.items(), key=lambda x: x[1])[0] if model_counts else 'no_model'
           
           return {
               'model': most_used_model,
               'tokens': {
                   'input': total_prompt_tokens,
                   'output': total_completion_tokens,
                   'total': total_tokens
               },
               'processing': {
                   'time': total_time,
                   'speed': avg_speed
               },
               'cost': total_cost
           }

       except Exception as e:
           raise

   def _get_prompt_usage(self) -> Dict:
       prompt_usage = {}
       for entry in self._usage_timeline:
           if entry.prompt_id:
               if entry.prompt_id not in prompt_usage:
                   prompt_usage[entry.prompt_id] = {
                       'total_tokens': 0,
                       'prompt_tokens': 0,
                       'completion_tokens': 0,
                       'total_cost': 0
                   }
               
               prompt_usage[entry.prompt_id]['total_tokens'] += entry.total_tokens
               prompt_usage[entry.prompt_id]['prompt_tokens'] += entry.prompt_tokens
               prompt_usage[entry.prompt_id]['completion_tokens'] += entry.completion_tokens
               prompt_usage[entry.prompt_id]['total_cost'] += entry.cost
       
       return prompt_usage

   def get_total_usage(self) -> Dict:
       return {
           'total_tokens': self._total_tokens,
           'total_prompt_tokens': self._total_prompt_tokens,
           'total_completion_tokens': self._total_completion_tokens
       }