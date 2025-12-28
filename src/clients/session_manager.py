"""
Entrez History session manager for multi-step pipelines.

Manages WebEnv and QueryKey for chaining E-utilities operations.
"""

from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass, field
import asyncio

from .eutilities import EUtilitiesClient
from ..utils.error_handler import PubMedError

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """Represents a step in a search pipeline."""
    step_number: int
    operation: str  # search, link, combine
    database: str
    query_key: str
    result_count: int
    parameters: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """
    Manages Entrez History Server sessions for complex pipelines.
    
    The History server allows chaining E-utilities operations without
    re-downloading intermediate results:
    
    1. ESearch (step 1) → stores results on History server
    2. ELink (step 2) → uses History to refine results
    3. EFetch (step 3) → fetches final results
    """
    
    def __init__(self, client: Optional[EUtilitiesClient] = None):
        """
        Initialize session manager.
        
        Args:
            client: E-Utilities client (creates new one if not provided)
        """
        self.client = client or EUtilitiesClient()
        self.web_env: Optional[str] = None
        self.steps: List[PipelineStep] = []
        self._step_counter = 0
    
    async def start_session(
        self,
        db: str,
        query: str
    ) -> PipelineStep:
        """
        Start a new session with an initial search.
        
        Args:
            db: Database to search
            query: Initial search query
            
        Returns:
            PipelineStep with results
        """
        result = await self.client.search(
            db=db,
            query=query,
            usehistory=True
        )
        
        self.web_env = result.get("web_env")
        query_key = result.get("query_key")
        
        if not self.web_env or not query_key:
            raise PubMedError(
                message="Failed to start session: no History data returned"
            )
        
        self._step_counter += 1
        step = PipelineStep(
            step_number=self._step_counter,
            operation="search",
            database=db,
            query_key=query_key,
            result_count=result.get("count", 0),
            parameters={"query": query}
        )
        
        self.steps.append(step)
        logger.info(f"Session started: {step.result_count} results (step {step.step_number})")
        
        return step
    
    async def add_search_step(
        self,
        db: str,
        query: str,
        combine_with: Optional[str] = None,
        combine_operator: str = "AND"
    ) -> PipelineStep:
        """
        Add a search step to the pipeline.
        
        Args:
            db: Database to search
            query: New search query
            combine_with: Query key to combine with (optional)
            combine_operator: How to combine (AND, OR, NOT)
            
        Returns:
            PipelineStep with new results
        """
        if not self.web_env:
            # Start new session if none exists
            return await self.start_session(db, query)
        
        # Build query with optional combination
        full_query = query
        if combine_with:
            full_query = f"#{combine_with} {combine_operator} ({query})"
        
        result = await self.client.search(
            db=db,
            query=full_query,
            usehistory=True
        )
        
        # Update web_env if changed
        if result.get("web_env"):
            self.web_env = result["web_env"]
        
        query_key = result.get("query_key")
        
        self._step_counter += 1
        step = PipelineStep(
            step_number=self._step_counter,
            operation="search",
            database=db,
            query_key=query_key,
            result_count=result.get("count", 0),
            parameters={
                "query": query,
                "combined_with": combine_with,
                "operator": combine_operator
            }
        )
        
        self.steps.append(step)
        logger.info(f"Search step added: {step.result_count} results (step {step.step_number})")
        
        return step
    
    async def add_link_step(
        self,
        from_db: str,
        to_db: str,
        link_name: Optional[str] = None,
        from_step: Optional[int] = None
    ) -> PipelineStep:
        """
        Add a link step to find related records.
        
        Args:
            from_db: Source database
            to_db: Target database
            link_name: Specific link name (optional)
            from_step: Step number to link from (uses last step if not specified)
            
        Returns:
            PipelineStep with linked results
        """
        if not self.web_env:
            raise PubMedError(
                message="Cannot add link step: no active session"
            )
        
        # Get query key from specified or last step
        if from_step:
            source_step = next(
                (s for s in self.steps if s.step_number == from_step),
                None
            )
            if not source_step:
                raise PubMedError(
                    message=f"Step {from_step} not found in pipeline"
                )
            query_key = source_step.query_key
        else:
            if not self.steps:
                raise PubMedError(
                    message="No previous steps in pipeline"
                )
            query_key = self.steps[-1].query_key
        
        result = await self.client.link(
            dbfrom=from_db,
            db=to_db,
            cmd="neighbor_history",
            query_key=query_key,
            web_env=self.web_env,
            linkname=link_name
        )
        
        # Extract new query key and count from linksets
        linksets = result.get("linksets", [])
        total_linked = sum(len(ls.get("ids", [])) for ls in linksets)
        
        # For neighbor_history, we get a new query key
        new_query_key = str(len(self.steps) + 1)  # Approximate
        
        self._step_counter += 1
        step = PipelineStep(
            step_number=self._step_counter,
            operation="link",
            database=to_db,
            query_key=new_query_key,
            result_count=total_linked,
            parameters={
                "from_db": from_db,
                "link_name": link_name,
                "from_step": from_step
            }
        )
        
        self.steps.append(step)
        logger.info(f"Link step added: {step.result_count} linked records (step {step.step_number})")
        
        return step
    
    async def fetch_results(
        self,
        step: Optional[int] = None,
        retmax: int = 500,
        retstart: int = 0,
        rettype: str = "abstract",
        retmode: str = "xml"
    ) -> str:
        """
        Fetch results from a pipeline step.
        
        Args:
            step: Step number to fetch from (uses last step if not specified)
            retmax: Maximum records to return
            retstart: Starting index
            rettype: Return type
            retmode: Return mode
            
        Returns:
            Raw response text
        """
        if not self.web_env:
            raise PubMedError(
                message="Cannot fetch: no active session"
            )
        
        # Get step to fetch from
        if step:
            source_step = next(
                (s for s in self.steps if s.step_number == step),
                None
            )
            if not source_step:
                raise PubMedError(
                    message=f"Step {step} not found in pipeline"
                )
        else:
            if not self.steps:
                raise PubMedError(
                    message="No steps in pipeline"
                )
            source_step = self.steps[-1]
        
        return await self.client.fetch(
            db=source_step.database,
            query_key=source_step.query_key,
            web_env=self.web_env,
            retmax=retmax,
            retstart=retstart,
            rettype=rettype,
            retmode=retmode
        )
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the pipeline execution.
        
        Returns:
            Dictionary with pipeline details
        """
        return {
            "web_env": self.web_env,
            "total_steps": len(self.steps),
            "steps": [
                {
                    "step": s.step_number,
                    "operation": s.operation,
                    "database": s.database,
                    "query_key": s.query_key,
                    "result_count": s.result_count,
                    "parameters": s.parameters
                }
                for s in self.steps
            ],
            "final_result_count": self.steps[-1].result_count if self.steps else 0
        }
    
    def reset(self) -> None:
        """Reset the session manager for a new pipeline."""
        self.web_env = None
        self.steps = []
        self._step_counter = 0
        logger.info("Session manager reset")
    
    async def close(self) -> None:
        """Close the E-Utilities client."""
        if hasattr(self.client, 'close'):
            await self.client.close()
