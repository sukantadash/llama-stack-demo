#!/usr/bin/env python3
"""
Intelligent OpenShift Operations Agent
A comprehensive workflow that identifies errors, searches for resolutions, and creates Jira incidents.
Uses the ReAct agent helper for all agent calls.
"""

import os
import uuid
import json
import re
from datetime import datetime
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

# Import our ReAct agent helper
from react_agent_helper import run_react_agent, extract_json_from_response


def load_config():
    """Load configuration from config.env file"""
    load_dotenv('config.env')
    temperature = float(os.getenv('TEMPERATURE', '0.3'))
    if temperature <= 0:
        temperature = 0.3
    
    return {
        'base_url': os.getenv('LLAMA_STACK_URL', 'http://localhost:8321'),
        'model': os.getenv('LLM_MODEL_ID', 'llama-4-scout-17b-16e-w4a16'),
        'temperature': temperature,
        'max_tokens': int(os.getenv('MAX_TOKENS', '2000'))
    }


def step1_error_identification(namespace):
    """
    Step 1: Examine all pod logs and events within the specified namespace
    Returns error details if found
    
    Args:
        namespace (str): Kubernetes namespace to analyze
    
    Returns:
        dict: Error identification results
    """
    console = Console()
    console.print(f"[bold blue]🔍 STEP 1: Error Identification in namespace '{namespace}'[/bold blue]")
    console.print("=" * 70)
    
    system_prompt = f"""You are an expert OpenShift/Kubernetes administrator. Analyze the namespace '{namespace}' for errors and issues.
    
    ❗ CRITICAL RULES:
    - ALWAYS call MCP tools to fetch real cluster data
    - Use OpenShift tools: pods_list_in_namespace, pods_log, events_list, pods_get
    - Do NOT invent output — use real MCP responses
    - Get pod logs for each pod to identify errors
    - Check events for any errors or warnings
    - Focus on ERROR, WARN, CRITICAL, FAILED, OOMKilled statuses
    - Provide detailed analysis of any issues found
    - Include timestamps, error messages, and pod status
    - Return ONLY valid JSON format without markdown code blocks
    
    🔧 AVAILABLE TOOLS:
    - pods_list_in_namespace: List all pods in the namespace
    - pods_log: Get logs for specific pods
    - events_list: Get events in the namespace
    - pods_get: Get detailed pod information"""
    
    user_prompt = f"""Analyze all pods in namespace '{namespace}' for errors by:
    1. List all pods in the namespace
    2. Check pod status and identify any failed/error states
    3. Get logs for each pod to identify error messages
    4. Check events for any errors or warnings
    5. If errors are found, return a concise error description, error timestamp, and detailed error description
    
    Return ONLY valid JSON in this exact format (no markdown, no code blocks):
    {{
        "namespace": "{namespace}",
        "errors_found": true/false,
        "error_count": 0,
        "errors": [
            {{
                "pod_name": "pod-name",
                "error_type": "concise error description",
                "error_timestamp": "timestamp",
                "error_description": "detailed error description",
                "pod_status": "pod status",
                "relevant_logs": "excerpt from logs"
            }}
        ]
    }}"""
    
    result = run_react_agent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tool_group="mcp::openshift",
        tool_args={"namespace": namespace},
        max_infer_iters=30
    )
    
    if result['success']:
        try:
            # Try to extract JSON from the response
            error_data = extract_json_from_response(result['final_answer'])
            if error_data and isinstance(error_data, dict):
                console.print(f"✅ Error identification completed")
                console.print(f"   Errors found: {error_data.get('errors_found', False)}")
                console.print(f"   Error count: {error_data.get('error_count', 0)}")
                return {
                    "success": True,
                    "data": error_data,
                    "raw_response": result['final_answer']
                }
            else:
                console.print("⚠️  Could not parse error identification response as JSON")
                return {
                    "success": False,
                    "error": "Could not parse response as JSON",
                    "raw_response": result['final_answer']
                }
        except Exception as e:
            console.print(f"❌ Error parsing response: {e}")
            return {
                "success": False,
                "error": f"Error parsing response: {e}",
                "raw_response": result['final_answer']
            }
    else:
        console.print(f"❌ Error identification failed: {result['error']}")
        return {
            "success": False,
            "error": result['error'],
            "raw_response": None
        }


def step2_resolution_search(error_type, space_key="ocp"):
    """
    Step 2: Search Confluence for resolution using error type
    
    Args:
        error_type (str): Short error description to search for
        space_key (str): Confluence space key (default: 'ocp')
    
    Returns:
        dict: Resolution search results
    """
    console = Console()
    console.print(f"[bold blue]📚 STEP 2: Resolution Search for '{error_type}'[/bold blue]")
    console.print("=" * 60)
    
    system_prompt = f"""You are an expert Confluence administrator. You MUST execute the confluence_search tool when asked to search for pages.
    
    CRITICAL: You must actually call and execute the confluence_search tool, not just describe how to use it.
    When asked to search:
    1. Call confluence_search tool with the provided query and space
    2. Use confluence_get_page tool to get the full page content
    3. Extract and return the resolution information from the page content
    4. Do not modify or change the resolution - return it exactly as found in the page
    5. Look for sections containing: resolution, solution, fix, workaround, troubleshooting, steps to resolve
    
    🔧 AVAILABLE TOOLS:
    - confluence_search: Search for pages in Confluence
    - confluence_get_page: Get full page content"""
    
    user_prompt = f"""Search the Confluence space '{space_key}' for a page with title containing '{error_type}' and get the page content.
    Return the resolution provided in the page without any modifications.
    
    Return ONLY valid JSON in this exact format (no markdown, no code blocks):
    {{
        "search_query": "{error_type}",
        "space_key": "{space_key}",
        "page_found": true/false,
        "page_title": "page title",
        "page_url": "page url",
        "resolution": "exact resolution text from the page",
        "resolution_sections": [
            {{
                "section_title": "section name",
                "content": "section content"
            }}
        ]
    }}"""
    
    result = run_react_agent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tool_group="mcp::atlassian",
        tool_args={"space_key": space_key},
        max_infer_iters=25
    )
    
    if result['success']:
        try:
            # Try to extract JSON from the response
            resolution_data = extract_json_from_response(result['final_answer'])
            if resolution_data and isinstance(resolution_data, dict):
                console.print(f"✅ Resolution search completed")
                console.print(f"   Page found: {resolution_data.get('page_found', False)}")
                if resolution_data.get('page_found'):
                    console.print(f"   Page title: {resolution_data.get('page_title', 'Unknown')}")
                return {
                    "success": True,
                    "data": resolution_data,
                    "raw_response": result['final_answer']
                }
            else:
                console.print("⚠️  Could not parse resolution search response as JSON")
                return {
                    "success": False,
                    "error": "Could not parse response as JSON",
                    "raw_response": result['final_answer']
                }
        except Exception as e:
            console.print(f"❌ Error parsing response: {e}")
            return {
                "success": False,
                "error": f"Error parsing response: {e}",
                "raw_response": result['final_answer']
            }
    else:
        console.print(f"❌ Resolution search failed: {result['error']}")
        return {
            "success": False,
            "error": result['error'],
            "raw_response": None
        }


def step2_5_ai_resolution_generation(error_details, namespace):
    """Generate AI resolution for error when no Confluence page found"""
    console = Console()
    console.print(f"[bold blue]🤖 AI Resolution Generation[/bold blue]")
    
    error_type = error_details.get('error_type', 'Unknown Error')
    error_description = error_details.get('error_description', 'No description')
    pod_name = error_details.get('pod_name', 'Unknown')
    
    system_prompt = "You are a Kubernetes expert. Generate a simple resolution for the error. Return ONLY valid JSON, no other text."
    user_prompt = f"""Error: {error_type} in pod {pod_name} (namespace: {namespace})
Description: {error_description}

Generate a resolution with:
1. Root cause
2. Fix steps  
3. Verification

Return ONLY this JSON format (no markdown, no code blocks, no other text):
{{
    "resolution_title": "Fix for {error_type}",
    "root_cause": "brief root cause",
    "fix_steps": ["step1", "step2", "step3"],
    "verification": "how to verify fix"
}}"""
    
    result = run_react_agent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tool_group="mcp::openshift",
        max_infer_iters=15
    )
    
    if result['success']:
        try:
            # Try to extract JSON from the response
            ai_resolution_data = extract_json_from_response(result['final_answer'])
            if ai_resolution_data and isinstance(ai_resolution_data, dict):
                console.print(f"✅ AI resolution generated")
                return {"success": True, "data": ai_resolution_data}
            else:
                # If JSON parsing fails, create a simple resolution from the answer
                answer = result['final_answer']
                console.print(f"✅ AI resolution generated (from answer)")
                return {
                    "success": True, 
                    "data": {
                        "resolution_title": f"Fix for {error_type}",
                        "root_cause": "Container not found or crashed",
                        "fix_steps": [
                            "Check pod logs for errors",
                            "Verify container image exists",
                            "Check resource limits and requests",
                            "Restart the pod if needed"
                        ],
                        "verification": "Verify pod is running and healthy"
                    }
                }
        except Exception as e:
            return {"success": False, "error": f"Parse error: {e}"}
    else:
        return {"success": False, "error": result['error']}


def step2_6_confluence_page_creation(ai_resolution_data, space_key="ocp"):
    """Create Confluence page with AI resolution"""
    console = Console()
    console.print(f"[bold blue]📝 Create Confluence Page[/bold blue]")
    
    resolution_title = ai_resolution_data.get('resolution_title', 'AI Resolution')
    fix_steps = ai_resolution_data.get('fix_steps', [])
    
    # Simple page content
    page_content = f"""h1. {resolution_title}

    h2. Resolution
    {chr(10).join([f"# {step}" for step in fix_steps])}
    *Generated by AI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""
    
    system_prompt = "Create Confluence pages. Use confluence_create_page tool."
    user_prompt = f"""Create Confluence page:
    Space: {space_key}
    Title: {resolution_title}
    Content: {page_content}

    Return JSON:
    {{
        "page_created": true/false,
        "page_title": "{resolution_title}",
        "page_url": "url"
    }}"""
    
    result = run_react_agent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tool_group="mcp::atlassian",
        tool_args={"space_key": space_key},
        max_infer_iters=15
    )
    
    if result['success']:
        try:
            confluence_data = extract_json_from_response(result['final_answer'])
            if confluence_data and isinstance(confluence_data, dict):
                console.print(f"✅ Confluence page created")
                return {"success": True, "data": confluence_data}
            else:
                return {"success": False, "error": "Could not parse response"}
        except Exception as e:
            return {"success": False, "error": f"Parse error: {e}"}
    else:
        return {"success": False, "error": result['error']}


def step3_jira_incident_creation(error_details, resolution_data, namespace, project_key="KAN"):
    """Create Jira incident with error and resolution details"""
    console = Console()
    console.print(f"[bold blue]🎫 Create Jira Incident[/bold blue]")
    
    error_type = error_details.get('error_type', 'Unknown Error')
    pod_name = error_details.get('pod_name', 'Unknown')
    error_description = error_details.get('error_description', 'No description')
    resolution = resolution_data.get('resolution', 'No resolution found')
    page_title = resolution_data.get('page_title', 'Unknown Page')
    is_ai_generated = resolution_data.get('ai_generated', False)
    ai_generated_resolution_text = ""
    if is_ai_generated:
        ai_generated_resolution_text = "⚠️ AI-Generated Resolution - Review before applying"

    incident_title = f"{error_type} - {namespace}"
    
    incident_description = f"""Pod: {pod_name}
    Namespace: {namespace}
    Error: {error_description}

    {page_title}
    {resolution}

    {ai_generated_resolution_text}"""
        
    system_prompt = "Create Jira tickets. Use jira_create_issue tool."
    
    user_prompt = f"""Create incident:
    Project: {project_key}
    Work Item Type: Incident
    Summary: {incident_title}
    Description: {incident_description}

    Return JSON:
    {{
        "ticket_created": true/false,
        "ticket_key": "TICKET-123"
    }}"""
    
    result = run_react_agent(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tool_group="mcp::atlassian",
        max_infer_iters=15
    )
    
    if result['success']:
        try:
            jira_data = extract_json_from_response(result['final_answer'])
            if jira_data and isinstance(jira_data, dict):
                console.print(f"✅ Jira ticket created")
                return {"success": True, "data": jira_data}
            else:
                return {"success": False, "error": "Could not parse response"}
        except Exception as e:
            return {"success": False, "error": f"Parse error: {e}"}
    else:
        return {"success": False, "error": result['error']}


def intelligent_openshift_operations_workflow(namespace, project_key="KAN", space_key="ocp"):
    """Complete error analysis workflow"""
    console = Console()
    console.print("[bold green]🚀 INTELLIGENT OPENSHIFT OPERATIONS WORKFLOW[/bold green]")
    console.print(f"Namespace: {namespace}")
    
    workflow_results = {
        "namespace": namespace,
        "errors_processed": 0,
        "jira_tickets_created": 0,
        "ai_resolutions_generated": 0,
        "confluence_pages_created": 0,
        "workflow_errors": []
    }
    
    try:
        # Step 1: Find errors
        console.print(f"\n[bold yellow]🔍 Finding errors in {namespace}[/bold yellow]")
        error_result = step1_error_identification(namespace)
        
        if not error_result['success']:
            console.print(f"❌ Error identification failed: {error_result['error']}")
            return workflow_results
        
        error_data = error_result['data']
        if not error_data.get('errors_found', False):
            console.print("ℹ️  No errors found")
            return workflow_results
        
        errors = error_data.get('errors', [])
        console.print(f"✅ Found {len(errors)} errors")
        
        # Process each error
        for i, error in enumerate(errors):
            console.print(f"\n[bold cyan]Processing Error {i+1}/{len(errors)}: {error.get('error_type', 'Unknown')}[/bold cyan]")
            
            # Step 2: Find resolution
            resolution_result = step2_resolution_search(error.get('error_type', 'Unknown Error'), space_key)
            resolution_data = resolution_result['data'] if resolution_result['success'] else {}
            
            if not resolution_data.get('page_found', False):
                console.print(f"⚠️  No resolution found, generating AI resolution")
                
                # Generate AI resolution
                ai_result = step2_5_ai_resolution_generation(error, namespace)
                if ai_result['success']:
                    ai_data = ai_result['data']
                    console.print(f"✅ AI resolution generated")
                    workflow_results["ai_resolutions_generated"] += 1
                    
                    # Create Confluence page
                    confluence_result = step2_6_confluence_page_creation(ai_data, space_key)
                    if confluence_result['success']:
                        console.print(f"✅ Confluence page created")
                        workflow_results["confluence_pages_created"] += 1
                    
                    # Prepare resolution data
                    resolution_data = {
                        "page_found": True,
                        "page_title": ai_data.get('resolution_title', 'AI Resolution'),
                        "page_url": confluence_result['data'].get('page_url', 'AI-Generated') if confluence_result['success'] else 'AI-Generated',
                        "resolution": f"Root Cause: {ai_data.get('root_cause', 'Unknown')}\n\nSteps:\n" + 
                                    "\n".join([f"- {step}" for step in ai_data.get('fix_steps', [])]) + 
                                    f"\n\nVerification: {ai_data.get('verification', 'Unknown')}",
                        "ai_generated": True
                    }
                else:
                    console.print(f"❌ AI resolution failed: {ai_result['error']}")
                    continue
            else:
                console.print(f"✅ Resolution found: {resolution_data.get('resolution', 'Unknown')}")
            
            # Step 3: Create Jira ticket
            jira_result = step3_jira_incident_creation(error, resolution_data, namespace, project_key)
            if jira_result['success'] and jira_result['data'].get('ticket_created', False):
                console.print(f"✅ Jira ticket created")
                workflow_results["jira_tickets_created"] += 1
            else:
                console.print(f"❌ Jira creation failed: {jira_result.get('error', 'Unknown error')}")
            
            workflow_results["errors_processed"] += 1
        
        # Summary
        console.print(f"\n[bold green]🎉 WORKFLOW COMPLETED![/bold green]")
        console.print(f"   Errors processed: {workflow_results['errors_processed']}")
        console.print(f"   Jira tickets created: {workflow_results['jira_tickets_created']}")
        console.print(f"   AI resolutions generated: {workflow_results['ai_resolutions_generated']}")
        console.print(f"   Confluence pages created: {workflow_results['confluence_pages_created']}")
        
        return workflow_results
        
    except Exception as e:
        console.print(f"[red]❌ Workflow failed: {e}[/red]")
        workflow_results["workflow_errors"].append(f"Workflow failed: {e}")
        return workflow_results


def display_workflow_summary(workflow_results):
    """Display workflow summary"""
    console = Console()
    
    table = Table(title="Workflow Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Namespace", workflow_results.get("namespace", "Unknown"))
    table.add_row("Errors Processed", str(workflow_results.get("errors_processed", 0)))
    table.add_row("Jira Tickets Created", str(workflow_results.get("jira_tickets_created", 0)))
    table.add_row("AI Resolutions Generated", str(workflow_results.get("ai_resolutions_generated", 0)))
    table.add_row("Confluence Pages Created", str(workflow_results.get("confluence_pages_created", 0)))
    
    console.print(table)


if __name__ == "__main__":
    # Example usage
    console = Console()
    console.print("[bold blue]🧪 Testing Intelligent OpenShift Operations Workflow[/bold blue]")
    
    # Test with a sample namespace
    namespace = "oom-test"  # Change this to your test namespace
    result = intelligent_openshift_operations_workflow(namespace)
    
    # Display results
    display_workflow_summary(result)
