# Customer Operations Agent

## Building an Intelligent Operations Agent for Enterprise OpenShift Clusters

Our operations team faces the challenges of managing a growing number of OpenShift clusters across multiple environments, often dealing with fragmented documentation, recurring incidents, and the need for repetitive troubleshooting. To alleviate cognitive overload and accelerate incident response, we are developing an advanced agent that integrates Retrieval-Augmented Generation (RAG) for knowledge retrieval, OpenShift control via a Model Context Protocol (MCP), and incident management through Jira integration.

**Vision:**

This agent aims to provide:

* **Intelligent Chat Functionality:** Leveraging Large Language Models (LLMs) for natural language interaction with operations teams.
* **Internal Knowledge Search (RAG):** Accessing and synthesizing information from internal confluence documentation for efficient troubleshooting.
* **External Knowledge Augmentation:** Searching external resources to supplement internal knowledge when needed.
* **OpenShift Interaction (Agent + MCP):** Executing commands and gathering information directly from OpenShift clusters.
* **Automated Incident Response:** Analyzing OpenShift pod logs, retrieving relevant solutions via RAG, summarizing the issue, and creating Jira incidents for tracking and resolution.
* **ServiceNow Integration (Phase 2):** Analyzing existing ServiceNow tickets to identify patterns and provide contextual solutions based on historical incident data.

## Comprehensive Notebook

**`customer_operations_agent.ipynb`:**
* **Focus:** Complete end-to-end demonstration of the intelligent operations agent, showcasing all capabilities in a single comprehensive workflow.
* **Capabilities Demonstrated:**
  - RAG-based knowledge retrieval from internal documentation
  - External web search for security advisories and best practices
  - OpenShift cluster monitoring and pod log analysis
  - Automated Jira incident creation and management
  - ServiceNow historical ticket analysis (Phase 2)
  - Intelligent decision making using ReAct framework
  - Prompt chaining for complex multi-step workflows

* **Complete Workflow Example:**
  1. **Initial Query:** "Check the status of pods running in ai-models namespace in 08d cluster and investigate any issues"
  2. **OpenShift Analysis:** Agent connects to OpenShift cluster, retrieves pod status and logs
  3. **Log Analysis:** Categorizes logs as normal or error, identifies specific issues
  4. **Knowledge Retrieval:** Uses RAG to search internal documentation for solutions
  5. **External Research:** Searches web for latest security advisories or known issues
  6. **ServiceNow Analysis:** (Phase 2) Reviews historical tickets for similar issues
  7. **Incident Creation:** Creates structured Jira incident with findings and recommendations
  8. **Summary & Next Steps:** Provides comprehensive summary with actionable next steps

* **Advanced Scenarios Covered:**
  - **Pod Failure Investigation:** Complete analysis from detection to resolution recommendations
  - **Security Incident Response:** Integration of security advisories with operational response
  - **Historical Pattern Analysis:** Leveraging ServiceNow data for predictive insights
  - **Multi-Environment Management:** Handling multiple clusters
  - **Automated Escalation:** Intelligent routing and priority assignment for incidents

## Key Features

1. **Jira Integration:** Automated incident creation and management for proper incident tracking and resolution.
2. **Enterprise Focus:** Tailored for enterprise environments with multiple OpenShift clusters across different environments.
3. **ServiceNow Integration:** Phase 2 addition for historical incident analysis and pattern recognition.
4. **Security Emphasis:** Enhanced focus on security advisories and compliance requirements.
5. **Structured Incident Management:** Automated creation of properly categorized and assigned Jira incidents with appropriate priority levels.
6. **Comprehensive Workflow:** Single notebook demonstrating complete operational intelligence capabilities.

## Getting Started

### Prerequisites
- Access to OpenShift clusters
- Jira instance access with appropriate permissions
- ServiceNow instance access (Phase 2)
- Internal knowledge base access for RAG functionality

### Environment Setup
1. Configure MCP servers for OpenShift, Jira, and ServiceNow
2. Set up RAG with internal documentation
3. Configure appropriate authentication and authorization
4. Set up monitoring and alerting for the agent's operations
