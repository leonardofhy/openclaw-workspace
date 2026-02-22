#!/usr/bin/env python3
"""
Generate outreach templates for different opportunity types.
"""

from typing import Dict, Any


TEMPLATES = {
    "consulting": {
        "short_dm": """Hi {name},
I'm a master's student at NTU (advised by Prof. Hung-yi Lee) with experience in {key_skill}. I help teams with {service_type} on a consulting basis (~5h/week).

Would you be open to a quick chat about {specific_need}?

Best,
Leo""",
        
        "cold_email": """Subject: {subject_line}

Hi {name},

I'm Leo, a master's student in EE/Telecom at National Taiwan University, advised by Prof. Hung-yi Lee (李宏毅). I specialize in {key_skill} and have worked on {project_example}.

I noticed {company_observation}. I help teams like yours with {service_offering} — typically 5-10 hours per week on a consulting basis.

Recent work includes:
• {achievement_1}
• {achievement_2}

Would you be open to a 15-minute call to discuss how I could help with {specific_problem}?

Best regards,
Leonardo (Leo) Hu
NTU EE/Telecom | {linkedin_url}""",
        
        "upwork_profile": """🎓 NTU Master's Student | ML/LLM Consultant | Research Engineer

I help startups and research teams build ML prototypes and LLM applications quickly.

**What I do:**
• ML model prototyping (PyTorch, TensorFlow)
• LLM integration (OpenAI, Anthropic APIs)
• Data pipeline design
• Research implementation

**Background:**
• Master's @ National Taiwan University (EE/Telecom)
• Advised by Prof. Hung-yi Lee (李宏毅)
• First-author paper (Interspeech 2026)
• 2 years industry experience

**Available:** ~5 hours/week for consulting engagements.

Let's build something together!"""
    },
    
    "tutoring": {
        "short_dm": """Hi! I'm a master's student at NTU (CS background) offering {subject} tutoring.

Rate: {rate_range} TWD/hr
Focus: {focus_area}

Interested in a trial session?""",
        
        "cold_email": """Subject: {subject} Tutoring - NTU Master's Student

Hi,

I'm offering {subject} tutoring for {target_audience}. I'm currently a master's student at NTU (EE/Telecom) with a strong CS background (NTU undergrad + 2 years industry).

**What I can help with:**
• {topic_1}
• {topic_2}
• {topic_3}

**Format:** Online or in-person (Taipei)
**Rate:** {rate_range} TWD/hour
**Trial:** First 30 minutes free

Available {availability}.

Let me know if you'd like to schedule a trial session!

Best,
Leo""",
        
        "upwork_profile": """💻 CS/ML Tutor | NTU Master's | Interview Prep Specialist

I help students and professionals master computer science fundamentals and prepare for technical interviews.

**Expertise:**
• Algorithms & Data Structures
• System Design
• Machine Learning
• Python programming

**Background:**
• Master's @ NTU (EE/Telecom)
• BS in Computer Science (NTU)
• 2 years industry experience
• Research focus: ML/AI

**Teaching style:** Patient, example-driven, focused on understanding over memorization.

Book a trial session!"""
    },
    
    "freelance": {
        "short_dm": """Hi {name},
I build {service_type} for startups. Recent project: {project_brief}.

Open to taking on 1-2 small projects (~5h/week). Interested?""",
        
        "cold_email": """Subject: {service_type} - Quick Turnaround

Hi {name},

I'm a freelance {role} based in Taipei. I help startups build {deliverable_type} quickly (typical turnaround: {timeline}).

**What I deliver:**
• {deliverable_1}
• {deliverable_2}
• {deliverable_3}

**Recent work:** {project_example}

**Tech stack:** {tech_stack}

I'm currently available for 1-2 small projects (~5-8 hours/week). Fixed-price or retainer options available.

Would you like to discuss {specific_need}?

Best,
Leo
{portfolio_url}""",
        
        "upwork_profile": """⚡ Fast ML Prototyping | LLM Applications | Research Engineer

I turn ML ideas into working prototypes. Fast.

**What I build:**
• LLM-powered applications
• ML model pipelines
• Data automation tools
• Proof-of-concept systems

**Tech:**
Python | PyTorch | OpenAI API | FastAPI | Docker

**Why work with me:**
• Academic rigor (NTU master's, Prof. 李宏毅 lab)
• Industry speed (2 years experience)
• Clear communication
• Fixed-price friendly

Available for small projects (~5-10h/week).

Let's ship something!"""
    },
    
    "grant": {
        "short_dm": """Hi {name},
I'm applying for {grant_name} with a project on {topic}. Would you be open to providing feedback on my proposal?

Background: {brief_background}""",
        
        "cold_email": """Subject: {grant_name} Application - Seeking Feedback

Hi {name},

I'm Leo, a master's student at NTU working on {research_area}. I'm applying for {grant_name} with a proposal on {project_title}.

**Project brief:** {one_line_description}

**Why this matters:** {impact_statement}

**My background:**
• Master's @ NTU (Prof. 李宏毅)
• {relevant_credential_1}
• {relevant_credential_2}

I'd greatly appreciate any feedback on my draft proposal, especially regarding {specific_feedback_area}.

Would you have 15 minutes for a quick call this week?

Best regards,
Leo
{contact_info}""",
        
        "upwork_profile": None  # N/A for grants
    }
}


def generate_template(
    opportunity_type: str,
    template_type: str,
    variables: Dict[str, str]
) -> str:
    """
    Generate outreach template.
    
    Args:
        opportunity_type: "consulting", "tutoring", "freelance", "grant"
        template_type: "short_dm", "cold_email", "upwork_profile"
        variables: Dict of template variables
    
    Returns:
        Formatted template string
    """
    if opportunity_type not in TEMPLATES:
        return f"Error: Unknown opportunity type '{opportunity_type}'"
    
    if template_type not in TEMPLATES[opportunity_type]:
        return f"Error: Unknown template type '{template_type}' for '{opportunity_type}'"
    
    template = TEMPLATES[opportunity_type][template_type]
    if template is None:
        return f"N/A: {template_type} not applicable for {opportunity_type}"
    
    try:
        return template.format(**variables)
    except KeyError as e:
        return f"Error: Missing variable {e} in template"


if __name__ == "__main__":
    # Test
    variables = {
        "name": "Alice",
        "key_skill": "LLM integration",
        "service_type": "ML prototyping",
        "specific_need": "your LLM pipeline"
    }
    
    print("=== SHORT DM (Consulting) ===")
    print(generate_template("consulting", "short_dm", variables))
    
    print("\n=== COLD EMAIL (Tutoring) ===")
    tutor_vars = {
        "subject": "Machine Learning",
        "target_audience": "grad school applicants",
        "topic_1": "ML fundamentals",
        "topic_2": "Interview prep (LeetCode)",
        "topic_3": "Research paper reading",
        "rate_range": "1000-1500",
        "availability": "weekday evenings"
    }
    print(generate_template("tutoring", "cold_email", tutor_vars))
