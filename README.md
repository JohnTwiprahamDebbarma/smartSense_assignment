# smartSense_assignment (TENTATIVE SOLUTION, AS I AM PLANNING TO DO)

# Board Meeting Management Agentic AI System

An intelligent, agent-based system that autonomously manages board meeting content - capturing, analyzing, summarizing, and tracking action items. The system reduces manual note-taking, improves clarity of outcomes, and ensures timely follow-through on board-level decisions using intelligent, goal-driven agents.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Agent Details](#agent-details)
- [Development](#development)
- [Docker Deployment](#docker-deployment)
- [License](#license)

## Overview

This system provides an end-to-end solution for managing board meeting content through a multi-agent architecture. It handles everything from speech-to-text transcription to decision tracking and follow-up task management.

The goal is to:
- Reduce manual note-taking during meetings
- Improve clarity of meeting outcomes
- Ensure timely follow-through on board-level decisions
- Provide audit-ready, accurate decision logs
- Automate the creation and tracking of action items

## System Architecture

The system follows a modular, agent-based architecture with specialized agents that collaborate through an event bus:

```
┌─────────────────┐          ┌───────────────────┐          ┌────────────────────┐          ┌─────────────────────┐
│ Transcriber     │          │ Semantic Parser   │          │ Decision Tracker   │          │ Orchestration       │
│ Agent           │───────▶  │ Agent             │───────▶  │ Agent              │───────▶  │ Agent               │
└─────────────────┘          └───────────────────┘          └────────────────────┘          └─────────────────────┘
        ▲                              ▲                              ▲                               ▲
        │                              │                              │                               │
        │                              │                              │                               │
        │                              │                              │                               │
        ▼                              ▼                              ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      Memory & Personalization Agent                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components

- **Core Framework**: Event-driven communication system and configuration management
- **Agent Ecosystem**: Specialized AI agents for different aspects of meeting management
- **Memory System**: Vector database for storing and retrieving meeting history and context
- **External Integrations**: Connections to task management tools, email, and messaging systems
- **Docker Deployment**: Containerized setup for easy deployment

## Key Features

- **Automated Transcription**: Convert meeting audio to structured text with speaker identification
- **Semantic Understanding**: Interpret the context, intent, and themes of discussions
- **Decision Extraction**: Identify and track formal decisions made during meetings
- **Action Item Management**: Create, assign, and track follow-up tasks
- **Risk Identification**: Flag potential issues and concerns raised during discussions
- **Intelligent Summarization**: Generate concise executive summaries of meetings
- **Follow-up Automation**: Send reminders and escalate overdue items
- **Personalization**: Learn stakeholder preferences and roles over time

## Prerequisites

- Python 3.8+
- Docker and Docker Compose (for containerized deployment)
- API keys for OpenAI or other LLM providers
- Access credentials for integrations (Jira, Slack, Email)

## Installation

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/smartsensesolutions/board-meeting-agent.git
   cd board-meeting-agent
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with required environment variables:
   ```
   OPENAI_API_KEY=your-openai-api-key
   JIRA_BASE_URL=your-jira-url
   JIRA_USERNAME=your-jira-username
   JIRA_API_TOKEN=your-jira-api-token
   SLACK_BOT_TOKEN=your-slack-bot-token
   SMTP_SERVER=your-smtp-server
   EMAIL_USERNAME=your-email-username
   EMAIL_PASSWORD=your-email-password
   ```

## Configuration

The system is configured through YAML files in the `config/` directory:

- `system_config.yaml`: Main configuration file for the entire system
- `agent_config.yaml`: Agent-specific configurations
- `prompts/`: Directory containing prompt templates for each agent

### Customizing Agent Behavior

I've designed the system so you can customize the behavior of each agent by modifying their respective configuration and prompt templates. For example:

1. Adjust confidence thresholds in `agent_config.yaml`:
   ```yaml
   agents:
     transcriber:
       confidence_threshold: 0.85
     semantic_parser:
       min_confidence_score: 0.7
   ```

2. Modify prompt templates in `prompts/<agent_name>_prompts.yaml` to change how agents interpret and process information.

## Usage

### Running the System

1. Start the main application:
   ```bash
   python main.py
   ```

2. Process a recorded meeting:
   ```bash
   python main.py --audio-file path/to/meeting_recording.wav --meeting-id board-meeting-2025-04-15
   ```

3. Start a live recording session:
   ```bash
   python main.py --live-recording --meeting-id board-meeting-2025-04-15
   ```

### API Endpoints

The system also provides a REST API for integration with other tools:

- `POST /api/meetings/start`: Start a new meeting recording
- `POST /api/meetings/stop`: Stop the current recording and process it
- `POST /api/meetings/process`: Process an uploaded audio file
- `GET /api/meetings/{meeting_id}/summary`: Get the summary of a meeting
- `GET /api/meetings/{meeting_id}/actions`: Get action items from a meeting

## Agent Details

### Transcriber Agent

I've implemented the Transcriber Agent to convert speech to text with speaker identification:

- Handles both live and recorded audio
- Identifies different speakers in the conversation
- Provides timestamps for each utterance
- Formats the transcript in a structured way

### Semantic Parser Agent

The Semantic Parser Agent interprets the meaning and context of discussions:

- Classifies the intent of each statement (suggesting, deciding, questioning, etc.)
- Identifies emerging themes (strategy, finance, operations, legal)
- Analyzes the flow and context of conversations
- Detects sentiment and tone

### Decision Tracker Agent

I've designed the Decision Tracker Agent to identify and organize key information:

- Generates executive summaries of meetings
- Extracts formal decisions with context and conditions
- Identifies action items with assignees and due dates
- Flags risks and concerns raised in discussions
- Notes unresolved questions for follow-up

### Orchestration Agent

The Orchestration Agent manages follow-up and integration:

- Creates tasks in external systems (e.g., Jira)
- Sends reminders for upcoming deadlines
- Escalates overdue items
- Distributes meeting summaries to stakeholders
- Adds unresolved items to future meeting agendas

### Memory & Personalization Agent

I've created the Memory Agent to provide historical context and personalization:

- Stores meeting history in a vector database
- Provides relevant context from past meetings
- Learns stakeholder roles and preferences
- Improves personalization over time
- Enhances context understanding across meetings

## Development

### Project Structure

```
board_meeting_agent/
│
├── agents/                 # Agent implementations
│   ├── base_agent.py       # Base class for all agents
│   ├── transcriber_agent.py
│   ├── semantic_parser_agent.py
│   ├── decision_tracker_agent.py
│   ├── orchestration_agent.py
│   └── memory_agent.py
│
├── core/                   # Core framework components
│   ├── config.py           # Configuration management
│   ├── event_bus.py        # Event-driven communication
│   ├── message.py          # Message definitions
│   └── orchestrator.py     # Main orchestration logic
│
├── memory/                 # Vector database and knowledge management
├── models/                 # Data models and schemas
├── utils/                  # Utility functions
├── config/                 # Configuration files
├── tests/                  # Unit and integration tests
└── docker/                 # Docker deployment files
```

### Adding a New Agent

1. Create a new file in the `agents/` directory
2. Inherit from the `BaseAgent` class
3. Implement the required abstract methods
4. Register the agent in the main orchestrator

### Testing

Run the test suite:

```bash
pytest
```

Run specific tests:

```bash
pytest tests/test_transcriber_agent.py
```

## Docker Deployment

To deploy the system using Docker:

1. Build the Docker image:
   ```bash
   docker build -t board-meeting-agent -f docker/Dockerfile .
   ```

2. Run with Docker Compose:
   ```bash
   docker-compose -f docker/docker-compose.yml up
   ```

I've designed the Docker Compose setup to include:
- The main application
- A vector database for memory storage
- A web interface for monitoring and management
