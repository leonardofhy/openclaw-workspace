#!/usr/bin/env python3
"""
Parse Leo's LaTeX resume and extract structured skills/experience/projects.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any


def parse_latex_file(filepath: Path) -> str:
    """Read LaTeX file and strip comments."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Remove LaTeX comments
    content = re.sub(r'%.*$', '', content, flags=re.MULTILINE)
    return content


def extract_skills(content: str) -> Dict[str, List[str]]:
    """Extract skills from LaTeX content."""
    skills = {
        "languages": [],
        "frameworks": [],
        "tools": [],
        "domains": []
    }
    
    # Look for skill sections
    # Pattern: \section{Skills} or similar
    skill_section = re.search(r'\\section\{Skills\}(.*?)(?=\\section|\Z)', content, re.DOTALL | re.IGNORECASE)
    if skill_section:
        skill_text = skill_section.group(1)
        
        # Extract bullet points or itemize
        items = re.findall(r'\\item\s+(.+?)(?=\\item|\Z)', skill_text, re.DOTALL)
        for item in items:
            clean_item = re.sub(r'\\[a-z]+(\{[^}]*\})?', '', item).strip()
            
            # Categorize based on keywords
            if any(kw in clean_item.lower() for kw in ['python', 'javascript', 'c++', 'java', 'rust', 'go']):
                skills["languages"].append(clean_item)
            elif any(kw in clean_item.lower() for kw in ['pytorch', 'tensorflow', 'react', 'django', 'flask']):
                skills["frameworks"].append(clean_item)
            elif any(kw in clean_item.lower() for kw in ['git', 'docker', 'aws', 'gcp', 'linux']):
                skills["tools"].append(clean_item)
            else:
                skills["domains"].append(clean_item)
    
    return skills


def extract_projects(content: str) -> List[Dict[str, Any]]:
    """Extract projects with descriptions."""
    projects = []
    
    # Pattern: \subsection{Project Name} followed by description
    project_matches = re.finditer(r'\\subsection\{(.+?)\}(.*?)(?=\\subsection|\\section|\Z)', content, re.DOTALL)
    
    for match in project_matches:
        title = match.group(1).strip()
        description_block = match.group(2)
        
        # Extract description from itemize or paragraph
        description = re.sub(r'\\[a-z]+(\{[^}]*\})?', '', description_block).strip()
        description = ' '.join(description.split())[:300]  # Truncate
        
        # Try to find URLs
        urls = re.findall(r'https?://[^\s\}]+', description_block)
        
        projects.append({
            "title": title,
            "description": description,
            "links": urls
        })
    
    return projects


def extract_experience(content: str) -> List[Dict[str, Any]]:
    """Extract work experience."""
    experiences = []
    
    # Look for experience section
    exp_section = re.search(r'\\section\{Experience\}(.*?)(?=\\section|\Z)', content, re.DOTALL | re.IGNORECASE)
    if exp_section:
        exp_text = exp_section.group(1)
        
        # Pattern: Company/Position entries
        entries = re.finditer(r'\\subsection\{(.+?)\}.*?\\textit\{(.+?)\}(.*?)(?=\\subsection|\Z)', exp_text, re.DOTALL)
        
        for entry in entries:
            position = entry.group(1).strip()
            timeframe = entry.group(2).strip()
            description = re.sub(r'\\[a-z]+(\{[^}]*\})?', '', entry.group(3)).strip()
            
            experiences.append({
                "position": position,
                "timeframe": timeframe,
                "description": ' '.join(description.split())[:300]
            })
    
    return experiences


def parse_resume(resume_dir: Path) -> Dict[str, Any]:
    """Parse complete resume structure."""
    resume_tex = resume_dir / "resume.tex"
    cv_dir = resume_dir / "cv"
    
    result = {
        "skills": {"languages": [], "frameworks": [], "tools": [], "domains": []},
        "projects": [],
        "experience": [],
        "education": []
    }
    
    # Parse main resume
    if resume_tex.exists():
        main_content = parse_latex_file(resume_tex)
        result["skills"] = extract_skills(main_content)
    
    # Parse cv subdirectory files
    if cv_dir.exists():
        for tex_file in cv_dir.glob("*.tex"):
            content = parse_latex_file(tex_file)
            
            if "project" in tex_file.stem.lower():
                result["projects"].extend(extract_projects(content))
            elif "experience" in tex_file.stem.lower():
                result["experience"].extend(extract_experience(content))
            elif "skill" in tex_file.stem.lower():
                extracted_skills = extract_skills(content)
                for key in extracted_skills:
                    result["skills"][key].extend(extracted_skills[key])
    
    # Deduplicate
    for key in result["skills"]:
        result["skills"][key] = list(set(result["skills"][key]))
    
    return result


if __name__ == "__main__":
    import sys
    
    resume_path = Path.home() / "Workspace" / "my_resume"
    if len(sys.argv) > 1:
        resume_path = Path(sys.argv[1])
    
    parsed = parse_resume(resume_path)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
