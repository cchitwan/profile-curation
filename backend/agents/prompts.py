# --- AI PROMPTS CONFIGURATION ---

JD_EXTRACTION_PROMPT = """
Extract the company name and target role from the following job description.
If not found, return 'Unknown'.

Job Description:
{jd_text}
"""

RESUME_PARSING_PROMPT = """
You are an expert resume parser. Extract the information from the raw resume text into a structured format.
Raw Text:
{raw_text}
"""

GAP_ANALYSIS_PROMPT = """
Compare the following resume against the job requirements. 
Identify missing skills, experience gaps, and areas for improvement.

CRITICAL CAREER ALIGNMENT CHECK:
Determine if the candidate's core profession matches the target role. 
Example: A Software Engineer applying for a Nursing or Insurance Advisor role is a CRITICAL MISMATCH.
If the industries or core expertise areas are fundamentally different:
1. Set 'is_aligned' to false.
2. Provide a blunt, professional explanation in 'alignment_feedback' why they shouldn't apply.
3. Suggest that curation may produce a 'fake' or 'forced' profile and advise against it.

Resume:
{resume}

Job Requirements:
{jd}

Skills to evaluate:
{skills_alignment}

Experience to evaluate:
{experience_alignment}
"""

CURATION_PROMPT = """
Tailor the following resume to match the job requirements. 

STRICT RULE:
- DO NOT invent or hallucinate experience, companies, or titles that do not exist in the original resume.
- If there is a role mismatch (e.g. Software Engineer applying for Advisor), do NOT try to make them look like an Advisor. Instead, highlight transferable skills (leadership, technical problem solving) while keeping their original titles and core responsibilities accurate.
- If the user explicitly confirmed they want to proceed despite a mismatch, focus on how their actual background could solve the employer's problems.

Resume:
{resume}

JD:
{jd}

Gap Report:
{gap}
"""

ATS_SCORING_PROMPT = """
You are a strictly critical ATS. Score this resume against the JD from 0 to 100.

BRUTAL DOMAIN ALIGNMENT RULE:
- If the candidate's core profession (e.g. Software Engineer) does not naturally transition to the target role (e.g. Insurance Advisor, Nurse, Pilot), you MUST score it between 0% and 15%.
- Do NOT give points for 'transferable skills' like 'Leadership' or 'Communication' if the technical domain mismatch is severe.
- A score of 80+ is reserved ONLY for candidates who have direct, relevant experience in the target industry and role level.

Resume:
{resume}

Job Requirements:
{jd}
"""
