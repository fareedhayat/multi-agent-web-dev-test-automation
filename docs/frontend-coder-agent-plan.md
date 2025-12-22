# Frontend Coder Agent Plan

## Overview
Create an autonomous agent that ingests UI requirements and produces frontend code, organizing the output in a predictable folder structure for ongoing development.

## Progress Tracker
- [x] Phase 1 — Input processing pipeline parses `requirements/feature-request.md` into structured data (screens, components, styling, functionality).
- [ ] Phase 2 — Planning pipeline converts structured data into a project/file manifest and prepares the output directories.
- [ ] Phase 3 — Code generation, validation, and file writing tools integrated with Microsoft Agent Framework runtime.

## Architecture Plan

### 1. Agent Core Components
- **Input Processing Module**
  - Parse natural language requirements (1-2 screens).
  - Extract key information: UI components, layout structure, styling preferences, interactions/functionality, data requirements.
- **Planning Module**
  - Break down requirements into actionable tasks.
  - Determine file structure.
  - Identify components to create.
  - Plan component hierarchy.
- **Code Generation Module**
  - Generate HTML/JSX files.
  - Create CSS/styling files.
  - Write JavaScript/TypeScript logic.
  - Generate configuration files.
- **File Management Module**
  - Create folder structure.
  - Write files to disk.
  - Organize assets.
  - Update imports/exports.

### Recommended Tools and Technologies
- **LLM Integration**: Azure OpenAI Service (GPT-4) or updated Microsoft Foundry equivalent for code generation and requirement analysis.
- **Code Generation Utilities**: Template engine (Handlebars/EJS), AST manipulation (Babel), formatting (Prettier), linting (ESLint).
- **File System Operations**: Python `os`, `pathlib`, `shutil`, `json`.
- **Frontend Framework Support**: React, Vue.js, Angular, or Vanilla HTML/CSS/JS (start with React).

## Implementation Steps

### Phase 1: Shared Configuration & Logging (Complete)
- Define `AGENT_CONFIG` with output directory, framework, styling, and retry defaults.
- Initialize module-level logger for consistent telemetry.
- Ensure functional style (no classes) to align with the latest Microsoft Agent Framework Python guidance for tool-centric agents.

### Phase 2: Define Agent Tools
1. **Requirements Analyzer**
   ```python
   def analyze_requirements(requirements: str) -> dict:
       """
       Analyzes user requirements and extracts structured data.
       Returns: {
           "screens": [],
           "components": [],
           "styling": {},
           "functionality": []
       }
       """
   ```
2. **File Structure Creator / Planner**
   ```python
   def plan_project_structure(structured_requirements: dict, config: dict) -> dict:
       """
       Produces directory + file manifest, e.g.:
       {
           "directories": ["components", ...],
           "files": [
               {"path": "pages/MarketplaceLanding.tsx", "type": "page", ...},
               ...
           ]
       }
       """
   ```
   ```python
   def ensure_project_structure(plan: dict) -> None:
       """Create directories listed in plan["directories"]."""
   ```
3. **Component Generator**
   ```python
   def generate_component(component_spec: dict) -> str:
       """Generates component code based on specifications."""
   ```
4. **Style Generator**
   ```python
   def generate_styles(styling_spec: dict) -> str:
       """Generates CSS/SCSS based on design requirements."""
   ```
5. **File Writer**
   ```python
   def write_file(path: str, content: str, file_type: str):
       """Writes generated code to appropriate files."""
   ```
6. **Code Validator**
   ```python
   def validate_code(code: str, language: str) -> dict:
       """Validates syntax and best practices."""
   ```

### Phase 3: Agent Workflow
1. Receive requirements.
2. Analyze and parse requirements (Tool 1).
3. Plan project structure and produce manifest (Tool 2).
4. Create folder structure from manifest (Tool 2 helper).
5. Generate components (Tool 3).
6. Generate styles (Tool 4).
7. Validate code (Tool 6).
8. Write files (Tool 5).
9. Generate summary report.

## Sample Configuration
```python
AGENT_CONFIG = {
    "output_directory": "./generated_frontend",
    "framework": "react",
    "styling": "css",
    "typescript": True,
    "template_directory": "./templates",
    "max_retries": 3,
    "validation": True
}
```

## Prompt Templates
- **System Prompt**: Expert frontend developer instructions for production-ready, accessible, responsive code.
- **User Prompt Template**: Parameterized prompt that injects framework, requirements, component name, styling approach, and required features.

## Error Handling and Validation
```python
class ValidationError(Exception):
    pass

def validate_and_retry(func):
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                result = func(*args, **kwargs)
                if validate_code(result):
                    return result
            except Exception as exc:
                if attempt == MAX_RETRIES - 1:
                    raise
                continue
    return wrapper
```

## Monitoring and Logging
- Use Python `logging` with logger name `frontend_coder_agent`.
- Log requirements intake, file creation, errors, and generation completion.

## Example Usage
```python
requirements = """
Create a user dashboard with:
1. Navigation bar with logo and menu
2. Sidebar with user profile
3. Main content area with data cards
4. Responsive design for mobile
"""

structured = analyze_requirements(requirements)
manifest = plan_project_structure(structured, AGENT_CONFIG)
ensure_project_structure(manifest, AGENT_CONFIG)
```

## Feature Request Context
- The current requirement is described in `requirements/feature-request.md` and targets a single SwapHub marketplace landing page.
- Generated assets must be placed under `artifacts/swaphub` and include `data-testid` attributes for interactive elements.
