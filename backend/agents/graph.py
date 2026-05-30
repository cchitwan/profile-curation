import json
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END
from models.state_models import GraphState
from agents.nodes import (
    parse_resume_node,
    extract_jd_node,
    analyze_gap_node,
    curate_resume_node,
    score_ats_node,
    route_evaluation
)
from database import SessionLocal
from models.db_models import CurationJob

def build_graph():
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("parse_resume", parse_resume_node)
    workflow.add_node("extract_jd", extract_jd_node)
    workflow.add_node("analyze_gap", analyze_gap_node)
    workflow.add_node("curate_resume", curate_resume_node)
    workflow.add_node("score_ats", score_ats_node)
    
    # Define edges
    workflow.set_entry_point("parse_resume")
    workflow.add_edge("parse_resume", "extract_jd")
    workflow.add_edge("extract_jd", "analyze_gap")
    workflow.add_edge("analyze_gap", "score_ats")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "score_ats",
        route_evaluation,
        {
            "end": END,
            "curate": "curate_resume"
        }
    )
    
    workflow.add_edge("curate_resume", "score_ats")
    
    return workflow.compile()

curation_graph = build_graph()

# Since we want HITL, we'll manually run parts of the logic or use subgraphs.
# For now, we'll just implement the helper functions for the two-step process.

def run_analysis_workflow(job_id, user_id, resume_text, job_input, is_url):
    initial_state = {
        "job_id": job_id,
        "raw_resume_text": resume_text,
        "job_input": job_input,
        "structured_resume": None,
        "job_requirements": None,
        "gap_report": None,
        "curated_resume": None,
        "score_report": None,
        "initial_score": None,
        "improvement_bullets": [],
        "token_usage": {"input": 0, "output": 0},
        "iteration_count": 0
    }
    
    # Phase 1: Parse -> Extract -> Analyze -> Score
    state = {**initial_state}
    state.update(parse_resume_node(state))
    state.update(extract_jd_node(state))
    state.update(analyze_gap_node(state))
    state.update(score_ats_node(state))
    
    # Save the initial results to the DB
    db = SessionLocal()
    job = db.query(CurationJob).filter(CurationJob.id == job_id).first()
    if job:
        job.initial_score = state["initial_score"]
        job.improvement_summary = json.dumps(state["gap_report"].get("improvement_areas", []))
        job.token_usage = json.dumps(state["token_usage"])
        db.commit()
    db.close()
    
    return {
        "job_id": job_id,
        "initial_score": state["initial_score"],
        "gap_report": state["gap_report"],
        "token_usage": state["token_usage"]
    }

def run_curation_from_analysis(job_id, user_id, resume_text, job_input, is_url):
    db = SessionLocal()
    job = db.query(CurationJob).filter(CurationJob.id == job_id).first()
    if not job:
        db.close()
        return

    # Initial State reconstruction
    existing_tokens = json.loads(job.token_usage) if job.token_usage else {"input": 0, "output": 0}
    state = {
        "job_id": job_id,
        "raw_resume_text": resume_text,
        "job_input": job_input,
        "structured_resume": None,
        "job_requirements": None,
        "gap_report": None,
        "curated_resume": None,
        "score_report": None,
        "initial_score": job.initial_score,
        "improvement_bullets": [],
        "token_usage": existing_tokens,
        "iteration_count": 0
    }

    # Run analysis steps again to rebuild state
    try:
        state.update(parse_resume_node(state))
        state.update(extract_jd_node(state))
        state.update(analyze_gap_node(state))
        state.update(score_ats_node(state))
    except Exception as e:
        print(f"Analysis rebuild failed: {e}")
        job.status = "failed"
        db.commit()
        db.close()
        return

    # KILL SWITCH: If not aligned, do not attempt curation
    is_aligned = state["gap_report"].get("is_aligned", True)
    
    if not is_aligned:
        print("--- ABORTING CURATION DUE TO MISMATCH ---")
        job.status = "completed"
        job.final_score = state["score_report"]["score"]
        job.improvement_summary = json.dumps(state["gap_report"].get("improvement_areas", []))
        job.token_usage = json.dumps(state["token_usage"])
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.close()
        return

    # Iterative Curation Loop
    max_iterations = 3
    while state.get("iteration_count", 0) < max_iterations:
        # Curate
        state.update(curate_resume_node(state))
        # Re-analyze and re-score
        state.update(analyze_gap_node(state))
        state.update(score_ats_node(state))
        
        # Check if we should stop
        if state["score_report"]["score"] >= 95:
            break

    # Save Final Result
    job.status = "completed"
    job.final_score = state["score_report"]["score"]
    job.curated_resume_json = json.dumps(state["curated_resume"])
    # Use improvement_bullets from curation, fallback to gap_report improvement_areas
    improvements = state.get("improvement_bullets") or state["gap_report"].get("improvement_areas", [])
    job.improvement_summary = json.dumps(improvements)
    job.token_usage = json.dumps(state["token_usage"])
    job.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.close()
