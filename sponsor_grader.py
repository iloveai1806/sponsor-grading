import logging
from typing import Dict, Any, Tuple
from openai import OpenAI
from config import config
from sheets_handler import SheetsHandler

logger = logging.getLogger(__name__)

class SponsorGrader:
    """AI-powered sponsor grading system using OpenAI with web search"""
    
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def research_and_grade_company(self, company_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Research a company and provide tier grading with reasoning
        
        Args:
            company_data: Dictionary containing company information from the sheet
            
        Returns:
            Tuple of (research_notes, decision)
        """
        company_name = company_data.get('Company Name', 'Unknown Company')
        website_url = company_data.get('Website URL', '')
        company_description = company_data.get('Company Description', '')
        
        # Build research prompt
        research_prompt = self._build_research_prompt(company_name, website_url, company_description)
        
        try:
            # Call OpenAI with web search
            response = self.client.responses.create(
                model="gpt-4.1",
                tools=[{"type": "web_search_preview"}],
                input=research_prompt,
                stream=True,
            )
            
            research_output = ""
            for event in response:
                if event.type == "response.output_text.delta":
                    research_output += event.delta
                    print(event.delta, end="", flush=True)
            
            # Extract sponsor category and reasoning from the response
            category, reasoning = self._extract_tier_and_reasoning(research_output)
            
            logger.info(f"Graded {company_name}: {category}")
            return research_output, f"{category} Sponsor: {reasoning}"
            
        except Exception as e:
            logger.error(f"Error researching {company_name}: {e}")
            return f"Research failed: {str(e)}", "Rejected Sponsor: Unable to complete research due to technical error"
    
    def _build_research_prompt(self, company_name: str, website_url: str, description: str) -> str:
        """Build comprehensive research prompt for OpenAI"""
        
        prompt = f"""
You are a professional sponsor evaluation analyst for Token Metrics. Your task is to thoroughly research and grade potential sponsors on a tier system (A, B, C).

Company Information:
- Name: {company_name}
- Website: {website_url}
- Description: {description}

Research Requirements:
1. Company Background & Legitimacy
   - Verify company existence and legitimacy
   - Check company registration, founding date, key personnel
   - Assess business model and core offerings

2. Financial Stability & Reputation
   - Look for funding rounds, revenue information, financial health
   - Check for any financial difficulties or bankruptcies
   - Assess market position and competitive standing

3. FUD (Fear, Uncertainty, Doubt) Analysis
   - Search for negative news, controversies, scandals
   - Check for regulatory issues, legal problems
   - Look for customer complaints, security breaches
   - Assess any reputational risks

4. Industry Standing
   - Evaluate industry reputation and peer recognition
   - Check for awards, certifications, partnerships
   - Assess leadership team credibility

Grading Criteria:
- Flagship Sponsors: Global leaders with strong brand equity and deep budgets. Excellent reputation, strong financials, no significant FUD, industry leader status.
- Eligible Sponsors: Solid, reputable brands that meet our standards but are not top tier. Good reputation, stable financials, minor concerns that don't significantly impact credibility.
- Rejected Sponsors: Entities that fail financial, brand-fit, or compliance checks. Poor reputation, financial instability, significant FUD, or high-risk factors.

Please provide:
1. A comprehensive research summary covering all areas above
2. Your final sponsor category recommendation (Flagship, Eligible, or Rejected)
3. A clear 2-3 sentence reasoning for your decision

Format your response exactly as follows (no markdown formatting, only plain text):
RESEARCH SUMMARY:
[Your detailed research findings]

SPONSOR DECISION: [Flagship/Eligible/Rejected]
REASONING: [2-3 sentence explanation]
"""
        
        return prompt
    
    def _extract_tier_and_reasoning(self, research_output: str) -> Tuple[str, str]:
        """Extract sponsor category and reasoning from OpenAI response"""
        try:
            # Look for sponsor decision in the response
            lines = research_output.split('\n')
            category = "Rejected"  # Default to most restrictive category if parsing fails
            reasoning = "Unable to parse sponsor decision from research output"
            
            for i, line in enumerate(lines):
                if "SPONSOR DECISION:" in line.upper():
                    decision_line = line.split(':')[-1].strip().upper()
                    if 'FLAGSHIP' in decision_line:
                        category = "Flagship"
                    elif 'ELIGIBLE' in decision_line:
                        category = "Eligible"
                    else:
                        category = "Rejected"
                
                if "REASONING:" in line.upper():
                    reasoning = line.split(':', 1)[-1].strip()
                    # Get additional lines if reasoning continues
                    j = i + 1
                    while j < len(lines) and lines[j].strip() and not lines[j].upper().startswith(('SPONSOR', 'RESEARCH', 'SUMMARY')):
                        reasoning += " " + lines[j].strip()
                        j += 1
                    break
            
            return category, reasoning
            
        except Exception as e:
            logger.error(f"Error extracting sponsor category and reasoning: {e}")
            return "Rejected", f"Error parsing research results: {str(e)}"
    
    def process_unprocessed_records(self, sheet_type: str = 'media', max_records: int = None):
        """Process all unprocessed records in a sheet"""
        try:
            # Connect to the appropriate sheet
            handler = SheetsHandler(sheet_type=sheet_type)
            
            # Get unprocessed records
            unprocessed_records = handler.get_unprocessed_records()
            
            if not unprocessed_records:
                print(f"No unprocessed records found in {sheet_type} sheet")
                return
            
            # Limit processing if specified
            if max_records:
                unprocessed_records = unprocessed_records[:max_records]
            
            print(f"Processing {len(unprocessed_records)} records from {sheet_type} sheet...")
            
            for i, record in enumerate(unprocessed_records):
                company_name = record.get('Company Name', 'Unknown')
                print(f"\nProcessing {i+1}/{len(unprocessed_records)}: {company_name}")
                
                # Research and grade the company
                research_notes, decision = self.research_and_grade_company(record)
                
                # Update the sheet
                row_index = record['_row_index']
                updates = {
                    'Research Notes': research_notes,
                    'Decision': decision
                }
                
                success = handler.update_record(row_index, updates)
                if success:
                    print(f"✓ Updated {company_name}: {decision.split(':')[0]}")
                else:
                    print(f"✗ Failed to update {company_name}")
            
            print(f"\nCompleted processing {len(unprocessed_records)} records")
            
        except Exception as e:
            logger.error(f"Error processing records: {e}")
            print(f"Error: {e}")

def main():
    """Main function to run the sponsor grading system"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Grade sponsor applications')
    parser.add_argument('--sheet-type', choices=['media', 'blog'], default='media',
                       help='Type of sheet to process (default: media)')
    parser.add_argument('--max-records', type=int,
                       help='Maximum number of records to process')
    
    args = parser.parse_args()
    
    # Validate configuration
    config.validate_config()
    
    # Create grader and process records
    grader = SponsorGrader()
    grader.process_unprocessed_records(
        sheet_type=args.sheet_type,
        max_records=args.max_records
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()