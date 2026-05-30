import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from models.state_models import (
    GraphState,
    StructuredResume,
    JobRequirements,
    GapReport,
    ScoreReport
)
import json
from agents.prompts import (
    JD_EXTRACTION_PROMPT,
    RESUME_PARSING_PROMPT,
    GAP_ANALYSIS_PROMPT,
    CURATION_PROMPT,
    ATS_SCORING_PROMPT
)

# Initialize LLM based on provider
provider = os.getenv("LLM_PROVIDER", "gemini").lower()

if provider == "openai":
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.2,
        max_retries=2
    )
elif provider == "anthropic":
    from langchain_anthropic import ChatAnthropic
    llm = ChatAnthropic(
        model_name=os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20240620"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.2,
        max_retries=2
    )
else:
    # Default to Gemini
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_NAME", "gemini-3.1-flash-lite-preview"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2,
        max_retries=2
    )

def track_tokens(state: GraphState, response_dict) -> Dict[str, int]:
    # response_dict comes from include_raw=True
    raw_message = response_dict.get("raw")
    input_tokens = 0
    output_tokens = 0
    
    if raw_message:
        # Try to get from usage_metadata (LangChain standard)
        usage = getattr(raw_message, 'usage_metadata', {})
        if not usage and isinstance(raw_message, dict):
            usage = raw_message.get('usage_metadata', {})
            
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        
        # Fallback for some Gemini versions
        if input_tokens == 0 and hasattr(raw_message, 'additional_kwargs'):
            usage_raw = raw_message.additional_kwargs.get('usage', {})
            input_tokens = usage_raw.get('prompt_tokens', 0)
            output_tokens = usage_raw.get('completion_tokens', 0)

    print(f"--- TOKENS TRACKED: In={input_tokens}, Out={output_tokens} ---")
    
    current_tokens = state.get("token_usage") or {"input": 0, "output": 0}
    return {
        "input": current_tokens["input"] + input_tokens,
        "output": current_tokens["output"] + output_tokens
    }

def parse_resume_node(state: GraphState) -> GraphState:
    print("--- PARSING RESUME ---")
    raw_text = state["raw_resume_text"]
    prompt = PromptTemplate.from_template(RESUME_PARSING_PROMPT)
    structured_llm = llm.with_structured_output(StructuredResume, include_raw=True)
    chain = prompt | structured_llm
    result = chain.invoke({"raw_text": raw_text})
    
    parsed = result["parsed"]
    resume_dict = parsed.dict()
    resume_dict["social_links"] = state.get("social_links", [])
    
    return {
        "structured_resume": resume_dict,
        "token_usage": track_tokens(state, result)
    }

def extract_jd_node(state: GraphState) -> GraphState:
    print("--- EXTRACTING JD ---")
    prompt = PromptTemplate.from_template(JD_EXTRACTION_PROMPT)
    structured_llm = llm.with_structured_output(JobRequirements, include_raw=True)
    chain = prompt | structured_llm
    result = chain.invoke({"jd_text": state["job_input"]})
    
    return {
        "job_requirements": result["parsed"].dict(),
        "token_usage": track_tokens(state, result)
    }

def analyze_gap_node(state: GraphState) -> GraphState:
    print("--- ANALYZING GAP ---")
    resume = state.get("curated_resume") or state["structured_resume"]
    jd = state["job_requirements"]
    prompt = PromptTemplate.from_template(GAP_ANALYSIS_PROMPT)
    structured_llm = llm.with_structured_output(GapReport, include_raw=True)
    chain = prompt | structured_llm
    result = chain.invoke({
        "resume": json.dumps(resume), 
        "jd": json.dumps(jd),
        "skills_alignment": resume.get("skills", []),
        "experience_alignment": resume.get("experience", [])
    })
    
    return {
        "gap_report": result["parsed"].dict(),
        "token_usage": track_tokens(state, result)
    }

class CurationResult(BaseModel):
    curated_resume: StructuredResume
    improvements: List[str]

def curate_resume_node(state: GraphState) -> GraphState:
    print("--- CURATING RESUME ---")
    resume = state.get("curated_resume") or state["structured_resume"]
    gap = state["gap_report"]
    jd = state["job_requirements"]
    
    prompt = PromptTemplate.from_template(CURATION_PROMPT)
    
    structured_llm = llm.with_structured_output(CurationResult, include_raw=True)
    chain = prompt | structured_llm
    result = chain.invoke({
        "resume": json.dumps(resume), 
        "jd": json.dumps(jd),
        "gap": json.dumps(gap)
    })
    
    parsed = result["parsed"]
    return {
        "curated_resume": parsed.curated_resume.dict(),
        "improvement_bullets": parsed.improvements,
        "token_usage": track_tokens(state, result),
        "iteration_count": state.get("iteration_count", 0) + 1
    }

def score_ats_node(state: GraphState) -> GraphState:
    print("--- SCORING RESUME ---")
    resume = state.get("curated_resume") or state["structured_resume"]
    jd = state["job_requirements"]
    
    prompt = PromptTemplate.from_template(ATS_SCORING_PROMPT)
    
    structured_llm = llm.with_structured_output(ScoreReport, include_raw=True)
    chain = prompt | structured_llm
    result = chain.invoke({"resume": json.dumps(resume), "jd": json.dumps(jd)})
    
    parsed = result["parsed"]
    report = parsed.dict()
    
    # Post-process: enforce domain mismatch penalty
    if report.get("domain_mismatch") is True:
        print("--- DOMAIN MISMATCH DETECTED: Forcing low score ---")
        report["score"] = min(report["score"], 15)
        
    updates = {
        "score_report": report,
        "token_usage": track_tokens(state, result)
    }
    
    # Set initial score only on first iteration
    if state.get("initial_score") is None:
        updates["initial_score"] = report["score"]
        
    return updates

class JDExtraction(BaseModel):
    company_name: str = Field(description="The name of the company hiring")
    target_role: str = Field(description="The job title or role name")

def extract_job_info_direct(job_input: str) -> Dict[str, str]:
    print("--- AUTO-EXTRACTING JD INFO ---")
    prompt = PromptTemplate.from_template(
        "Extract the Company Name and Job Title from the following job description. "
        "If you cannot find one, use 'Unknown'.\n\nJob Description:\n{job_input}"
    )
    structured_llm = llm.with_structured_output(JDExtraction)
    chain = prompt | structured_llm
    result = chain.invoke({"job_input": job_input})
    return result.dict()

def route_evaluation(state: GraphState):
    score = state["score_report"]["score"]
    iteration = state.get("iteration_count", 0)
    print(f"--- SCORE: {score}, ITERATION: {iteration} ---")
    
    if score >= 95 or iteration >= 3:
        return "end"
    else:
        return "curate"
