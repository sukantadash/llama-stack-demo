# Pod Logs Analyzer

A simple function to analyze pod logs in any Kubernetes namespace and return an error summary using ReActAgent with OpenShift MCP tools.

## Files

- `pod_logs_analyzer_simple.ipynb` - Jupyter notebook with examples and testing
- `pod_logs_analyzer.py` - Standalone Python module for easy import

## Quick Start

### 1. Install Dependencies

```bash
pip install llama-stack-client python-dotenv
```

### 2. Configure Environment

Create a `config.env` file:

```env
LLAMA_STACK_URL=http://localhost:8321
LLM_MODEL_ID=r1-qwen-14b-w4a16
TEMPERATURE=0.0
MAX_TOKENS=4096
MAX_INFER_ITERATIONS=10
```

### 3. Use the Function

```python
from pod_logs_analyzer import analyze_pod_logs

# Analyze pods in a namespace
result = analyze_pod_logs("my-namespace")

if result['success']:
    print(f"Found {len(result['critical_issues'])} critical issues")
    print(result['summary'])
else:
    print(f"Analysis failed: {result['summary']}")
```

### 4. Command Line Usage

```bash
python pod_logs_analyzer.py oom-test
```

## Function Signature

```python
def analyze_pod_logs(namespace, client=None, model_id=None, max_infer_iters=None):
    """
    Analyze pod logs in a given namespace and return error summary.
    
    Args:
        namespace (str): The Kubernetes namespace to analyze
        client: Optional LlamaStackClient instance
        model_id: Optional model ID
        max_infer_iters: Optional max iterations
    
    Returns:
        dict: Error summary with success, namespace, summary, errors, warnings, 
              critical_issues, recommendations, and execution_steps
    """
```

## Return Format

The function returns a dictionary with the following structure:

```python
{
    'success': bool,                    # Whether analysis succeeded
    'namespace': str,                   # Analyzed namespace
    'summary': str,                     # Detailed analysis summary
    'errors': list,                     # List of errors found
    'warnings': list,                   # List of warnings found
    'critical_issues': list,            # List of critical issues
    'recommendations': list,            # List of recommendations
    'execution_steps': int              # Number of execution steps
}
```

## Features

- ✅ Simple one-line function call
- ✅ Automatic error handling
- ✅ Structured return format
- ✅ Configurable parameters
- ✅ Works with any namespace
- ✅ Uses ReActAgent with MCP tools
- ✅ Returns categorized results
- ✅ Command-line interface
- ✅ Graceful dependency handling

## Error Handling

The function handles missing dependencies gracefully and provides helpful error messages. If `llama_stack_client` is not available, it will return a structured error response with installation instructions.

## Examples

### Basic Usage

```python
result = analyze_pod_logs("oom-test")
print(f"Analysis successful: {result['success']}")
print(f"Critical issues: {len(result['critical_issues'])}")
```

### With Custom Parameters

```python
from llama_stack_client import LlamaStackClient

client = LlamaStackClient(base_url="http://localhost:8321")
result = analyze_pod_logs("my-namespace", client=client, model_id="custom-model")
```

### Check for Specific Issues

```python
result = analyze_pod_logs("my-namespace")
if "OOM" in str(result['critical_issues']):
    print("Out of Memory issues detected!")
```
