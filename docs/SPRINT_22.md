# Sprint 22 — Project Generation Orchestrator Layer

This document outlines the architecture, pipeline flow, class dependencies, and future extensibility of the AI Project Orchestrator introduced in Sprint 22.

---

## 1. Architecture

Sprint 22 introduces a decoupled, stage-based orchestration layer that structures project creation into consecutive, isolated steps. This prevents business logic and state management from leaking into the core pipeline execution model.

The architecture comprises three main components:
1. **`PipelineContext`**: A unified state object that is passed through and modified by all pipeline stages.
2. **`PipelineStage`**: An abstract interface defining the contract for all processing steps.
3. **`ProjectPipeline`**: An orchestrator that loads the project, builds the initial context, runs all registered stages sequentially, handles failures, and returns a detailed `ProductionSummary`.

---

## 2. Pipeline Flow Diagram

The project generation flow is sequenced as follows:

```mermaid
flowchart LR
    Start([Start Project Generation]) --> Load[Load Project from DB]
    Load --> Context[Initialize PipelineContext]
    Context --> Stage1[Stage 1: StoryStage]
    Stage1 -->|"Populates Story, Episodes, Scenes"| Stage2[Stage 2: JobBuilderStage]
    Stage2 -->|"Populates GenerationJobs"| End([Generate ProductionSummary])
```

---

## 3. Class Diagram

```mermaid
classDiagram
    class ProjectPipeline {
        -db: Session
        +stages: List~PipelineStage~
        +generate_project(project_id: int, variables: dict) ProductionSummary
    }

    class PipelineContext {
        +project: Project
        +story: Story
        +episodes: List~Episode~
        +scenes: List~Scene~
        +generation_jobs: List~GenerationJob~
        +metadata: dict
        +warnings: List~str~
        +errors: List~str~
        +status: str
        +timestamps: dict~str, datetime~
    }

    class PipelineStage {
        <<interface>>
        +run(context: PipelineContext) PipelineContext
    }

    class StoryStage {
        -db: Session
        -generator: StoryGenerator
        +run(context: PipelineContext) PipelineContext
    }

    class JobBuilderStage {
        -db: Session
        -builder: JobBuilder
        +run(context: PipelineContext) PipelineContext
    }

    class JobBuilder {
        -db: Session
        +build_jobs(scenes: List~Scene~) List~GenerationJob~
    }

    class ProductionSummary {
        +project_id: int
        +story_id: int
        +episode_count: int
        +scene_count: int
        +job_count: int
        +estimated_duration: float
        +pipeline_duration: float
        +status: str
    }

    ProjectPipeline --> PipelineStage : Executes
    PipelineStage <|-- StoryStage : Inherits
    PipelineStage <|-- JobBuilderStage : Inherits
    JobBuilderStage --> JobBuilder : Utilizes
    StoryStage ..> PipelineContext : Modifies
    JobBuilderStage ..> PipelineContext : Modifies
    ProjectPipeline ..> ProductionSummary : Produces
```

---

## 4. Execution Sequence

The complete E2E execution lifecycle runs synchronously within a database transaction boundary:

```mermaid
sequenceDiagram
    autonumber
    actor Client as API / Client
    participant PP as ProjectPipeline
    participant Context as PipelineContext
    participant SS as StoryStage
    participant JBS as JobBuilderStage
    participant JB as JobBuilder

    Client->>PP: generate_project(project_id, variables)
    PP->>PP: Query project configuration from DB
    PP->>Context: Instantiate(project, variables)
    
    Note over PP, SS: Start Execution of Registered Stages
    
    PP->>SS: run(context)
    Note over SS: Generate story structure via StoryGenerator
    SS-->>PP: Updated context (Story, Episodes, Scenes)
    
    PP->>JBS: run(context)
    JBS->>JB: build_jobs(context.scenes)
    Note over JB: Create & Save GenerationJobs
    JB-->>JBS: List[GenerationJob]
    JBS-->>PP: Updated context (GenerationJobs)
    
    PP->>PP: Calculate estimated & pipeline durations
    PP-->>Client: ProductionSummary
```

---

## 5. Future Stages

The stage-based architecture is designed for plug-and-play expansion. Future sprints can register additional stages in `ProjectPipeline.stages` without rewriting existing code:

1. **`CharacterRegistryStage`**: Analyzes the generated story and auto-registers new Characters and Character-Scene associations in the database.
2. **`ShotPlannerStage`**: Breaks down generated scene narration into granular camera shots and cinematic sequences.
3. **`AssetAllocationStage`**: Directs the pre-production layout, locating reusable background layouts and setting references.
