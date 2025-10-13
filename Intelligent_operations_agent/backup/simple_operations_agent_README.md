# Simple Operations Agent - 3-Step Workflow

A Jupyter notebook that demonstrates a simple 3-step operations workflow using Llama Stack with MCP (Model Context Protocol) servers.

## Overview

This notebook provides a streamlined operations agent that:

1. **Step 1**: Searches for pod logs in the `oom-test` namespace and summarizes error messages using `mcp::openshift`
2. **Step 2**: Searches Confluence pages in the `OCP` space for solutions using `mcp::atlassian`
3. **Step 3**: Creates a Jira incident in the `KAN` project with resolution details using `mcp::atlassian`

## Prerequisites

- Python 3.13+
- Llama Stack server running on `http://localhost:8321`
- MCP servers configured for OpenShift and Atlassian
- Access to the target OpenShift cluster
- Access to Confluence and Jira instances

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   - Update `config.env` with your settings
   - Ensure Llama Stack server is running
   - Verify MCP servers are configured

3. **Run the notebook**:
   - Open `simple_operations_agent.ipynb` in Jupyter
   - Run cells in order
   - Use the Quick Test cell to verify functionality

## Configuration

- **Namespace**: `oom-test`
- **Confluence Space**: `OCP`
- **Jira Project**: `KAN`
- **MCP Tools**: `mcp::openshift` and `mcp::atlassian`

## Usage Options

1. **Individual Steps**: Run each step separately for debugging
2. **Complete Workflow**: Run all 3 steps in one session
3. **Quick Test**: Simple test to verify functionality

## Troubleshooting

The notebook includes comprehensive troubleshooting sections:

- Configuration validation
- Tool availability checks
- Error handling with helpful messages
- Common issue solutions

## Features

- ✅ **Error Handling**: Comprehensive error handling and validation
- ✅ **Tool Validation**: Checks for required MCP tools
- ✅ **Streaming Support**: Real-time response streaming
- ✅ **Troubleshooting**: Built-in diagnostics and solutions
- ✅ **Modular Design**: Individual steps or complete workflow

## Files

- `simple_operations_agent.ipynb` - Main notebook
- `requirements.txt` - Python dependencies
- `config.env` - Configuration file
- `simple_operations_agent_README.md` - This file

## Support

For issues or questions:
1. Check the troubleshooting section in the notebook
2. Verify Llama Stack server is running
3. Check MCP server configuration
4. Review error messages for specific guidance
