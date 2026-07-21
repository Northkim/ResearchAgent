# ReAgent Project Development Plan

## 1. Project Vision

ReAgent is a web-based research agent platform designed for long-running autonomous research workflows.

The goal is not to build a simple chatbot, but to build agent infrastructure that allows users to create research projects, define workflows, provide materials, and let AI agents continuously perform research tasks while maintaining memory, state, and generated artifacts.

The final system should allow users to:

1. Create a research project through a web interface.
2. Upload research materials.
3. Select a research workflow.
4. Launch an autonomous agent.
5. Monitor agent progress.
6. Review generated research artifacts.
7. Continue previous research sessions without losing context.

## 2. Core Design Philosophy

The system follows three principles.

### 2.1 Persistent Agent

Agents should maintain knowledge across sessions.

The system should support:

- project memory
- execution history
- progress tracking
- state recovery

### 2.2 Workflow-driven Research

Research tasks should be represented as reusable workflows.

Examples:

- Literature Search
- Idea Generation
- Paper Writing
- Paper Review
- Experiment Reproduction

### 2.3 Platform-oriented Architecture

The system should eventually become a deployable web platform.

The architecture should separate:

- Agent Runtime
- Workflow Engine
- Skill System
- Backend Services
- Frontend Interface

## 3. High-level Architecture

```text
                    Web Frontend
                         |
                  Backend Platform
                         |
        -------------------------------------
        |                  |                |
  Workflow Engine     Agent Manager    Skill Manager
        |                  |                |
        -------------------------------------
                         |
                   Agent Runtime
                         |
                LLM + Tools + Memory
```

## 4. Main Development Modules

### Module 1: Agent Runtime Core

Purpose:

Build the foundation that allows an AI agent to understand tasks and execute work.

Responsibilities:

- workspace management
- instruction loading
- context management
- memory management
- execution state

Expected structure:

```text
project/
├── AGENT.md
├── config.yaml
├── inputs/
├── outputs/
├── memory/
├── skills/
└── logs/
```

### Module 2: Workflow Engine

Purpose:

Transform research processes into executable workflows.

Responsibilities:

- workflow definition
- workflow execution
- task dependencies
- checkpoints

Example:

```text
Literature Search
        |
        v
Search Papers
        |
        v
Read Papers
        |
        v
Extract Knowledge
        |
        v
Generate Report
```

### Module 3: Skill System

Purpose:

Provide reusable capabilities for agents.

Examples:

- paper search
- PDF parsing
- citation management
- code execution
- experiment running

Each skill should contain:

- metadata
- implementation
- documentation

### Module 4: Memory and State System

Purpose:

Enable long-running research.

The system should support:

- Short-term state: current execution state
- Working memory: current task context
- Long-term memory: historical knowledge

### Module 5: Artifact Management

Purpose:

Manage research outputs.

Artifacts include:

- reports
- papers
- experiment results
- generated code

Requirements:

- version tracking
- metadata
- retrieval

### Module 6: Backend Platform

Purpose:

Provide cloud services.

Responsibilities:

- user management
- project management
- workflow management
- API management

Suggested technology:

- FastAPI
- PostgreSQL
- Redis

### Module 7: Web Frontend

Purpose:

Provide a user interface.

Main pages:

- dashboard
- project workspace
- workflow selection
- agent monitoring
- artifact viewer

Suggested technology:

- React
- Next.js

### Module 8: Monitoring and Evaluation

Purpose:

Make agent behavior observable.

Track:

- execution logs
- tool calls
- errors
- generated artifacts
- workflow status

## 5. Recommended Development Order

### Step 1: Define Architecture

Deliver:

- system architecture
- folder structure
- data models
- workflow specification

### Step 2: Implement Agent Runtime

Deliver:

- workspace parser
- agent context
- memory manager
- execution state

### Step 3: Implement Workflow Engine

Deliver:

- workflow schema
- workflow executor
- checkpoint system

### Step 4: Implement Skill System

Deliver:

- skill registry
- skill loading
- tool execution

### Step 5: Implement Artifact and Logging System

Deliver:

- artifact storage
- execution records

### Step 6: Build Backend API

Deliver:

- project API
- workflow API
- execution API

### Step 7: Build Web Interface

Deliver:

- user dashboard
- project management
- agent monitoring

## 6. Engineering Requirements

The project should prioritize:

- modular architecture
- clean interfaces
- testability
- documentation
- extensibility

The system should avoid:

- hard-coded workflows
- single-agent assumptions
- tightly coupled components

## 7. Current Development Goal

The first implementation goal is **not** the full web platform.

The first goal is to build a reliable Agent Runtime and Workflow foundation that can later be deployed as a web service.

Current priority:

1. Architecture design
2. Agent Runtime prototype
3. Workflow abstraction
4. Persistent memory system
