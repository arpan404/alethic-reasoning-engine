"""Vector search tools for Alethic agents.

These tools provide semantic search capabilities using pgvector
for finding similar candidates, resumes, and matching queries.
"""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.embeddings import Embedding, EmbeddingEntityType, EmbeddingModel
from database.models.candidates import Candidate
from database.models.applications import Application
from database.models.jobs import Job

logger = logging.getLogger(__name__)


async def search_candidates_semantic(
    query: str,
    job_id: Optional[int] = None,
    limit: int = 10,
    min_similarity: float = 0.5,
    include_rejected: bool = False,
) -> Dict[str, Any]:
    """Semantically search for candidates matching a query.
    
    Uses vector embeddings to find candidates whose resume/profile
    best matches the natural language query.
    
    Examples:
    - "React developers with 5+ years experience"
    - "Machine learning engineers who worked at FAANG"
    - "Product managers with healthcare background"
    
    Args:
        query: Natural language search query
        job_id: Optional filter to specific job applications
        limit: Maximum number of results
        min_similarity: Minimum similarity score (0-1)
        include_rejected: Whether to include rejected applications
        
    Returns:
        Dictionary with ranked matching candidates
    """
    # First, get embedding for the query
    query_embedding = await _get_query_embedding(query)
    
    if not query_embedding:
        return {
            "success": False,
            "error": "Failed to generate embedding for query",
        }
    
    async with AsyncSessionLocal() as session:
        # Build the similarity search query using pgvector
        # Using cosine similarity: 1 - (embedding <=> query_vector)
        similarity_sql = text("""
            WITH candidate_embeddings AS (
                SELECT 
                    e.entity_id as candidate_id,
                    1 - (e.embedding_vector <=> :query_vector) as similarity,
                    ROW_NUMBER() OVER (PARTITION BY e.entity_id ORDER BY e.chunk_index) as rn
                FROM embeddings e
                WHERE e.entity_type = 'candidate'
                AND 1 - (e.embedding_vector <=> :query_vector) >= :min_similarity
            )
            SELECT candidate_id, MAX(similarity) as similarity
            FROM candidate_embeddings
            WHERE rn = 1
            GROUP BY candidate_id
            ORDER BY similarity DESC
            LIMIT :limit
        """)
        
        result = await session.execute(
            similarity_sql,
            {
                "query_vector": str(query_embedding),
                "min_similarity": min_similarity,
                "limit": limit * 2,  # Get extra for filtering
            }
        )
        similarity_results = result.fetchall()
        
        if not similarity_results:
            return {
                "success": True,
                "query": query,
                "matches": [],
                "total": 0,
                "message": "No matching candidates found",
            }
        
        candidate_ids = [r[0] for r in similarity_results]
        similarity_map = {r[0]: float(r[1]) for r in similarity_results}
        
        # Get candidate details
        query_builder = (
            select(Candidate)
            .where(Candidate.id.in_(candidate_ids))
        )
        
        # Filter by job if specified
        if job_id:
            query_builder = (
                query_builder
                .join(Application)
                .where(Application.job_id == job_id)
            )
            if not include_rejected:
                query_builder = query_builder.where(Application.status != "rejected")
        
        candidates_result = await session.execute(query_builder)
        candidates = candidates_result.scalars().all()
        
        # Build results with similarities
        matches = []
        for candidate in candidates:
            similarity = similarity_map.get(candidate.id, 0)
            matches.append({
                "candidate_id": candidate.id,
                "name": f"{candidate.first_name} {candidate.last_name}".strip(),
                "headline": candidate.headline,
                "email": candidate.email,
                "location": candidate.location,
                "experience_level": candidate.experience_level,
                "years_of_experience": candidate.years_of_experience,
                "skills": (candidate.skills or [])[:10],
                "similarity_score": round(similarity, 4),
            })
        
        # Sort by similarity
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        matches = matches[:limit]
        
        return {
            "success": True,
            "query": query,
            "job_id": job_id,
            "matches": matches,
            "total": len(matches),
        }


async def find_similar_candidates(
    reference_candidate_id: int,
    job_id: Optional[int] = None,
    limit: int = 10,
    min_similarity: float = 0.6,
) -> Dict[str, Any]:
    """Find candidates similar to a reference candidate.
    
    Useful for:
    - Finding more candidates like a good hire
    - Exploring similar profiles in the talent pool
    
    Args:
        reference_candidate_id: The candidate to find similar profiles to
        job_id: Optional filter to specific job
        limit: Maximum number of results
        min_similarity: Minimum similarity threshold
        
    Returns:
        Dictionary with similar candidates
    """
    async with AsyncSessionLocal() as session:
        # Get reference candidate's embedding
        ref_embedding_query = select(Embedding).where(
            Embedding.entity_type == EmbeddingEntityType.CANDIDATE,
            Embedding.entity_id == reference_candidate_id,
            Embedding.chunk_index == 0,  # Primary embedding
        )
        ref_result = await session.execute(ref_embedding_query)
        ref_embedding = ref_result.scalar_one_or_none()
        
        if not ref_embedding:
            return {
                "success": False,
                "error": f"No embedding found for candidate {reference_candidate_id}",
            }
        
        # Find similar candidates
        similarity_sql = text("""
            SELECT 
                e.entity_id as candidate_id,
                1 - (e.embedding_vector <=> :ref_vector) as similarity
            FROM embeddings e
            WHERE e.entity_type = 'candidate'
            AND e.entity_id != :ref_id
            AND e.chunk_index = 0
            AND 1 - (e.embedding_vector <=> :ref_vector) >= :min_similarity
            ORDER BY similarity DESC
            LIMIT :limit
        """)
        
        result = await session.execute(
            similarity_sql,
            {
                "ref_vector": str(ref_embedding.embedding_vector),
                "ref_id": reference_candidate_id,
                "min_similarity": min_similarity,
                "limit": limit * 2,
            }
        )
        similar_results = result.fetchall()
        
        if not similar_results:
            return {
                "success": True,
                "reference_candidate_id": reference_candidate_id,
                "similar_candidates": [],
                "total": 0,
            }
        
        candidate_ids = [r[0] for r in similar_results]
        similarity_map = {r[0]: float(r[1]) for r in similar_results}
        
        # Get candidate details
        query = select(Candidate).where(Candidate.id.in_(candidate_ids))
        candidates_result = await session.execute(query)
        candidates = candidates_result.scalars().all()
        
        similar = []
        for candidate in candidates:
            similarity = similarity_map.get(candidate.id, 0)
            similar.append({
                "candidate_id": candidate.id,
                "name": f"{candidate.first_name} {candidate.last_name}".strip(),
                "headline": candidate.headline,
                "location": candidate.location,
                "experience_level": candidate.experience_level,
                "skills": (candidate.skills or [])[:10],
                "similarity_score": round(similarity, 4),
            })
        
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        similar = similar[:limit]
        
        return {
            "success": True,
            "reference_candidate_id": reference_candidate_id,
            "similar_candidates": similar,
            "total": len(similar),
        }


async def match_candidates_to_job(
    job_id: int,
    limit: int = 20,
    min_similarity: float = 0.5,
    stage_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Find candidates that best match a job description semantically.
    
    Uses the job's ideal candidate description and requirements
    to find the best matching candidates from the talent pool.
    
    Args:
        job_id: The job to match candidates against
        limit: Maximum number of results
        min_similarity: Minimum similarity threshold
        stage_filter: Optional filter by application stage
        
    Returns:
        Dictionary with ranked matching candidates
    """
    async with AsyncSessionLocal() as session:
        # Get job details for context
        job_query = select(Job).where(Job.id == job_id)
        job_result = await session.execute(job_query)
        job = job_result.scalar_one_or_none()
        
        if not job:
            return {
                "success": False,
                "error": f"Job {job_id} not found",
            }
        
        # Get job embedding
        job_embedding_query = select(Embedding).where(
            Embedding.entity_type == EmbeddingEntityType.JOB,
            Embedding.entity_id == job_id,
            Embedding.chunk_index == 0,
        )
        job_emb_result = await session.execute(job_embedding_query)
        job_embedding = job_emb_result.scalar_one_or_none()
        
        if not job_embedding:
            # If no job embedding, create query from job data
            job_text = f"{job.title}. {job.ideal_candidate_description or ''} Skills: {', '.join(job.required_skills or [])}"
            query_embedding = await _get_query_embedding(job_text)
            if not query_embedding:
                return {
                    "success": False,
                    "error": "Could not generate job embedding",
                }
        else:
            query_embedding = job_embedding.embedding_vector
        
        # Find matching candidates who applied to this job
        similarity_sql = text("""
            SELECT 
                e.entity_id as candidate_id,
                a.id as application_id,
                a.current_stage,
                a.ai_overall_score,
                1 - (e.embedding_vector <=> :job_vector) as semantic_similarity
            FROM embeddings e
            JOIN applications a ON a.candidate_id = e.entity_id
            WHERE e.entity_type = 'candidate'
            AND e.chunk_index = 0
            AND a.job_id = :job_id
            AND a.status != 'rejected'
            AND 1 - (e.embedding_vector <=> :job_vector) >= :min_similarity
            ORDER BY semantic_similarity DESC
            LIMIT :limit
        """)
        
        params = {
            "job_vector": str(query_embedding),
            "job_id": job_id,
            "min_similarity": min_similarity,
            "limit": limit,
        }
        
        result = await session.execute(similarity_sql, params)
        matches = result.fetchall()
        
        # Get candidate details
        candidate_ids = [r[0] for r in matches]
        candidates_query = select(Candidate).where(Candidate.id.in_(candidate_ids))
        candidates_result = await session.execute(candidates_query)
        candidates = {c.id: c for c in candidates_result.scalars().all()}
        
        ranked_matches = []
        for row in matches:
            candidate_id, application_id, stage, ai_score, similarity = row
            candidate = candidates.get(candidate_id)
            
            if stage_filter and stage != stage_filter:
                continue
            
            if candidate:
                # Combine semantic similarity with AI score
                combined_score = (float(similarity) * 0.6 + (float(ai_score or 0) / 100) * 0.4)
                
                ranked_matches.append({
                    "candidate_id": candidate_id,
                    "application_id": application_id,
                    "name": f"{candidate.first_name} {candidate.last_name}".strip(),
                    "headline": candidate.headline,
                    "current_stage": stage,
                    "ai_score": float(ai_score) if ai_score else None,
                    "semantic_similarity": round(float(similarity), 4),
                    "combined_score": round(combined_score, 4),
                    "skills": (candidate.skills or [])[:10],
                })
        
        # Sort by combined score
        ranked_matches.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return {
            "success": True,
            "job_id": job_id,
            "job_title": job.title,
            "matches": ranked_matches,
            "total": len(ranked_matches),
        }


async def vectorize_candidate(
    candidate_id: int,
    include_resume: bool = True,
    include_experience: bool = True,
) -> Dict[str, Any]:
    """Vectorize/re-vectorize a candidate's profile and documents.
    
    Queues the embedding generation for a candidate's profile,
    resume, and experience data.
    
    Args:
        candidate_id: The candidate to vectorize
        include_resume: Whether to vectorize resume content
        include_experience: Whether to include work experience
        
    Returns:
        Dictionary with task status
    """
    # Verify candidate exists
    async with AsyncSessionLocal() as session:
        query = select(Candidate).where(Candidate.id == candidate_id)
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return {
                "success": False,
                "error": f"Candidate {candidate_id} not found",
            }
    
    # Queue vectorization task
    from agents.tools.queue import enqueue_task
    task_result = await enqueue_task(
        task_type="vectorize_candidate",
        payload={
            "candidate_id": candidate_id,
            "include_resume": include_resume,
            "include_experience": include_experience,
        },
        priority="normal",
    )
    
    logger.info(f"Queued vectorization for candidate {candidate_id}")
    
    return {
        "success": True,
        "candidate_id": candidate_id,
        "task_id": task_result.get("task_id"),
        "message": "Candidate vectorization queued",
    }


async def _get_query_embedding(query: str) -> Optional[List[float]]:
    """Generate embedding for a text query.
    
    In production, this would call the embedding service.
    """
    # Queue embedding generation and wait for result
    # For now, return a placeholder - in production this would
    # call OpenAI/Cohere/etc. embedding API
    from agents.tools.queue import enqueue_task, get_task_status
    import asyncio
    
    task_result = await enqueue_task(
        task_type="generate_embedding",
        payload={"text": query},
        priority="high",
    )
    
    task_id = task_result.get("task_id")
    
    # Wait for embedding (in production, would use proper async waiting)
    # For now, return None to indicate async processing needed
    logger.info(f"Embedding generation queued: {task_id}")
    
    # In a real implementation, we'd wait for the task or
    # call the embedding API synchronously
    return None
