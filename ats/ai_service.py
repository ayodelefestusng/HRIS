"""
ATS AI Service for resume parsing and candidate evaluation using Google Gemini API
"""

import logging
import json
import mimetypes
from pathlib import Path
import google.generativeai as genai
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Configure Gemini API
API_KEY = "AIzaSyAUkb4Lb_fdqZnb4jL4e12ZoqRVm0PIkQ4"
genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash-lite"


class ResumeValidationError(ValidationError):
    """Custom exception for resume validation errors."""
    pass


class ATSAIService:
    """Service for AI-powered ATS operations."""
    
    ALLOWED_FORMATS = {'.pdf', '.doc', '.docx'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @staticmethod
    def validate_resume_file(resume_file):
        """
        Validate resume file format and size.
        
        Args:
            resume_file: Django UploadedFile object
            
        Returns:
            bool: True if valid
            
        Raises:
            ResumeValidationError: If file is invalid
        """
        if not resume_file:
            raise ResumeValidationError("No resume file provided.")
        
        # Check file size
        if resume_file.size > ATSAIService.MAX_FILE_SIZE:
            raise ResumeValidationError(
                f"File size exceeds maximum allowed size of {ATSAIService.MAX_FILE_SIZE / 1024 / 1024:.1f}MB. "
                f"Your file is {resume_file.size / 1024 / 1024:.1f}MB."
            )
        
        # Check file extension
        file_ext = Path(resume_file.name).suffix.lower()
        if file_ext not in ATSAIService.ALLOWED_FORMATS:
            raise ResumeValidationError(
                f"Invalid file format: {file_ext}. Accepted formats are: {', '.join(ATSAIService.ALLOWED_FORMATS)}"
            )
        
        return True
    
    @staticmethod
    def extract_resume_data(resume_file):
        """
        Extract structured data from resume using Gemini API.
        
        Args:
            resume_file: Django UploadedFile object
            
        Returns:
            dict: Extracted resume data including skills, experience, education
        """
        try:
            # Validate file first
            ATSAIService.validate_resume_file(resume_file)
            
            # Read file content
            file_content = resume_file.read()
            resume_file.seek(0)  # Reset file pointer
            
            # Prepare file for Gemini
            mime_type, _ = mimetypes.guess_type(resume_file.name)
            if not mime_type:
                mime_type = 'application/pdf'
            
            # Create message with file
            message = f"""
            Please analyze this resume and extract the following information in JSON format:
            {{
                "full_name": "...",
                "email": "...",
                "phone": "...",
                "summary": "...",
                "skills": ["skill1", "skill2", ...],
                "work_experiences": [
                    {{
                        "company": "...",
                        "position": "...",
                        "start_date": "YYYY-MM-DD",
                        "end_date": "YYYY-MM-DD or null if current",
                        "description": "..."
                    }}
                ],
                "education": [
                    {{
                        "institution": "...",
                        "qualification": "Bachelor's/Master's/etc",
                        "field": "...",
                        "year": "YYYY"
                    }}
                ],
                "key_competencies": ["competency1", "competency2", ...]
            }}
            
            Return ONLY valid JSON, no additional text.
            """
            
            # Upload file to Gemini
            try:
                uploaded_file = genai.upload_file(
                    path=resume_file.temporary_file_path() if hasattr(resume_file, 'temporary_file_path') else resume_file,
                    mime_type=mime_type
                )
                
                # Send to Gemini with file
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content([
                    message,
                    uploaded_file
                ])
                
                # Parse response
                response_text = response.text.strip()
                
                # Clean JSON if wrapped in markdown code blocks
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                extracted_data = json.loads(response_text)
                return extracted_data
                
            except Exception as api_error:
                logger.error(f"Gemini API error: {str(api_error)}")
                raise ResumeValidationError(f"Error processing resume: {str(api_error)}")
            
        except ResumeValidationError:
            raise
        except Exception as e:
            logger.error(f"Error extracting resume data: {str(e)}")
            raise ResumeValidationError(f"Failed to process resume: {str(e)}")
    
    @staticmethod
    def analyze_application_fit(candidate_data, job_posting):
        """
        Analyze how well a candidate fits a job posting using AI.
        
        Args:
            candidate_data: dict with candidate info and resume data
            job_posting: JobPosting instance
            
        Returns:
            dict: Analysis results with insights and recommendations
        """
        try:
            prompt = f"""
            Analyze how well this candidate fits the job posting:
            
            CANDIDATE PROFILE:
            - Skills: {', '.join(candidate_data.get('skills', []))}
            - Experience: {json.dumps(candidate_data.get('work_experiences', []))}
            - Education: {json.dumps(candidate_data.get('education', []))}
            - Competencies: {', '.join(candidate_data.get('key_competencies', []))}
            
            JOB REQUIREMENTS:
            - Description: {job_posting.description}
            - Requirements: {job_posting.requirements}
            
            Provide analysis in JSON format:
            {{
                "overall_fit_score": 0-100,
                "strengths": ["strength1", "strength2", ...],
                "gaps": ["gap1", "gap2", ...],
                "missing_skills": ["skill1", "skill2", ...],
                "recommendations": "...",
                "valuable_insights": "Notable skills or experience relevant to role..."
            }}
            
            Return ONLY valid JSON.
            """
            
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            
            response_text = response.text.strip()
            
            # Clean JSON if wrapped in markdown
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            analysis = json.loads(response_text)
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing application fit: {str(e)}")
            return {
                "overall_fit_score": 0,
                "strengths": [],
                "gaps": [],
                "missing_skills": [],
                "recommendations": f"Could not analyze due to error: {str(e)}",
                "valuable_insights": ""
            }
    
    @staticmethod
    def generate_ai_comments(candidate_data, job_posting, analysis_results):
        """
        Generate human-readable AI comments from analysis results.
        
        Args:
            candidate_data: dict with extracted resume data
            job_posting: JobPosting instance
            analysis_results: dict from analyze_application_fit
            
        Returns:
            str: Formatted AI comments for recruiter review
        """
        comments = []
        
        comments.append(f"**AI CANDIDATE ANALYSIS FOR: {job_posting.title}**\n")
        comments.append(f"Overall Fit Score: {analysis_results.get('overall_fit_score', 0)}/100\n")
        
        if analysis_results.get('strengths'):
            comments.append("**Strengths:**")
            for strength in analysis_results['strengths']:
                comments.append(f"• {strength}")
        
        if analysis_results.get('gaps'):
            comments.append("\n**Experience Gaps:**")
            for gap in analysis_results['gaps']:
                comments.append(f"• {gap}")
        
        if analysis_results.get('missing_skills'):
            comments.append("\n**Missing Skills:**")
            for skill in analysis_results['missing_skills']:
                comments.append(f"• {skill}")
        
        if analysis_results.get('valuable_insights'):
            comments.append(f"\n**Valuable Insights:**\n{analysis_results['valuable_insights']}")
        
        if analysis_results.get('recommendations'):
            comments.append(f"\n**Recommendations:**\n{analysis_results['recommendations']}")
        
        return "\n".join(comments)
