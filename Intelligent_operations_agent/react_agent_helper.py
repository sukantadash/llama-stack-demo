#!/usr/bin/env python3
"""
Generic ReAct Agent Helper
A reusable function for making ReAct agent calls with custom system prompts, user prompts, and tool groups.
Based on patterns from logfileanalysis.py and tools.py
"""

import os
import uuid
import json
import re
from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.react.agent import ReActAgent
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput
from rich.console import Console
from dotenv import load_dotenv


def load_config():
    """Load configuration from config.env file"""
    load_dotenv('config.env')

    return {
        'base_url': os.getenv('LLAMA_STACK_URL', 'http://localhost:8321'),
        'model': os.getenv('LLM_MODEL_ID', 'llama-4-scout-17b-16e-w4a16'),
        'temperature': float(os.getenv('TEMPERATURE', '0.3')),
        'max_tokens': int(os.getenv('MAX_TOKENS', '2000'))
    }


def extract_json_from_response(response_text):
    """
    Extract JSON from a response that might contain markdown formatting
    
    Args:
        response_text (str): Response text that might contain JSON in markdown code blocks
    
    Returns:
        dict: Parsed JSON data or None if extraction fails
    """
    try:
        # First try to parse the entire response as JSON
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_patterns = [
        r'```json\s*\n(.*?)\n```',  # ```json ... ```
        r'```\s*\n(.*?)\n```',      # ``` ... ```
        r'`(.*?)`',                  # `...`
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    # Try to find JSON-like content in the response
    # Look for content that starts with { and ends with }
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            # Try to fix incomplete JSON by adding missing closing brackets
            json_text = json_match.group()
            try:
                # Count opening and closing braces
                open_braces = json_text.count('{')
                close_braces = json_text.count('}')
                missing_braces = open_braces - close_braces
                
                if missing_braces > 0:
                    # Add missing closing braces
                    json_text += '}' * missing_braces
                    return json.loads(json_text)
            except json.JSONDecodeError:
                pass
    
    return None


def run_react_agent(system_prompt, user_prompt, tool_group, tool_args=None, max_infer_iters=20):
    """
    Run a ReAct agent with custom system prompt, user prompt, and tool group
    
    Args:
        system_prompt (str): System instructions for the agent
        user_prompt (str): User prompt/query
        tool_group (str): Tool group to use (e.g., "mcp::atlassian", "mcp::openshift")
        tool_args (dict, optional): Additional tool arguments
        max_infer_iters (int): Maximum inference iterations (default: 20)
    
    Returns:
        dict: Response with success status, final answer, and raw response
    """
    console = Console()
    config = load_config()
    
    try:
        # Initialize client
        client = LlamaStackClient(base_url=config['base_url'])
        
        # Prepare tool configuration
        tool_config = {}
        if tool_args:
            tool_config.update(tool_args)
        
        # Create ReActAgent with specified tool group
        agent = ReActAgent(
            client=client,
            model=config['model'],
            tools=[tool_group],
            response_format={
                "type": "json_schema",
                "json_schema": ReActOutput.model_json_schema(),
            },
            sampling_params={
                "strategy": {"type": "greedy"},
                "max_tokens": config['max_tokens'],
                "temperature": config['temperature'],
            },
            max_infer_iters=max_infer_iters
        )
        
        # Create session
        session_id = agent.create_session(session_name=f"react_agent_{uuid.uuid4()}")
        console.print(f"[green]✅ Session created: {session_id}[/green]")
        
        # Build the complete prompt with system instructions
        full_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}"
        
        console.print(f"[yellow]🤖 Running ReAct Agent with tool group: {tool_group}[/yellow]")
        console.print(f"[cyan]System Prompt: {system_prompt}...[/cyan]")
        console.print(f"[cyan]User Prompt: {user_prompt}...[/cyan]")
        console.print("-" * 60)
        
        # Create turn with the prompt
        response = agent.create_turn(
            messages=[{"role": "user", "content": full_prompt}],
            session_id=session_id,
            stream=False
        )
        
        # Extract the response content
        response_content = response.output_message.content
        console.print(f"[green]✅ Response received:[/green]")
        console.print(response_content, markup=False)
        
        # Try to extract final answer from ReAct response
        final_answer = None
        try:
            # Parse the ReAct response to extract final answer
            react_data = extract_json_from_response(response_content)
            if react_data and isinstance(react_data, dict):
                final_answer = react_data.get('answer', response_content)
            else:
                final_answer = response_content
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not parse ReAct response: {e}[/yellow]")
            final_answer = response_content
        
        return {
            "success": True,
            "final_answer": final_answer,
            "raw_response": response_content,
            "session_id": session_id,
            "tool_group": tool_group
        }
        
    except Exception as e:
        console.print(f"[red]❌ ReAct Agent failed: {e}[/red]")
        return {
            "success": False,
            "error": str(e),
            "final_answer": None,
            "raw_response": None,
            "session_id": None,
            "tool_group": tool_group
        }
