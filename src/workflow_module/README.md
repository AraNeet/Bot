# Workflow Module - Architecture Documentation

## Overview

The Workflow Module provides a unified system for executing automated workflows with integrated action execution, verification, and error handling.

## Structure

```
workflow_module/
├── engine_1/                     # Workflow orchestration
│   ├── process_input.py          # Main entry point (process_input_workflow)
│   ├── workflow_executor.py      # Execution engine (execute instructions/objectives/workflow)
│   ├── workflow_planner.py       # Objective planning and preparation
│   └── instruction_loader.py     # Instruction loading and parameter filling
├── actions_2/                    # Action execution system
│   ├── unified_executor.py       # Main executor (action + verification + error handling)
│   ├── action_list.json          # List of all actions that can be completed
│   ├── handlers/                 # Individual action handlers (numbered)
│   │   ├── 1_open_multinetwork_instructions_page.py
│   │   ├── 2_enter_advertiser_name.py
│   │   ├── 3_enter_deal_number.py
│   │   ├── 4_enter_agency.py
│   │   ├── 5_enter_begin_date.py
│   │   ├── 6_enter_end_date.py
│   │   ├── 7_click_search_button.py
│   │   ├── 8_wait_for_search_results.py
│   │   ├── 9_find_row_by_values.py
│   │   └── 10_select_edit_multinetwork_instruction.py
│   ├── helpers/                  # Utility modules used by handlers
│   │   ├── actions.py            # Low-level automation (keyboard, mouse)
│   │   ├── verification_utils.py # Verification utilities (OCR extraction, similarity)
│   │   ├── computer_vision_utils.py  # Computer vision utilities
│   │   ├── ocr_utils.py          # OCR utilities
│   │   └── table_utils.py        # Table processing utilities
│   └── assets/                   # Image assets for template matching
└── objective_definitions/        # Objective definition JSON files
    └── edit_copy_definition.json
```

## Components

### 1. Engine Module (`engine_1/`)

**Purpose**: High-level workflow orchestration and planning

**Files**:
- `process_input.py`: Main entry point - contains `process_input_workflow()` function that orchestrates planning, execution, and summary printing
- `workflow_executor.py`: Execution engine - executes instructions, objectives, and complete workflow
- `workflow_planner.py`: Plans objectives and prepares instructions with parameters
- `instruction_loader.py`: Loads instruction JSON files and fills parameters

**Responsibilities**:
1. **process_input.py**: Main entry point with `process_input_workflow()` that coordinates planning → execution → summary printing (all in one function)
2. **workflow_executor.py**: Executes instructions via unified_executor, tracks progress, handles errors
3. **workflow_planner.py**: Loads objectives, prepares instructions with parameters
4. **instruction_loader.py**: Loads and processes instruction JSON files

### 2. Action Module (`actions_2/`)

**Purpose**: Action execution with integrated verification and error handling

**Files**:
- `unified_executor.py`: Main executor that handles action → verification → error handling flow
- `action_list.json`: List of all actions that can be completed, mapping action types to handler modules
- `handlers/`: Individual handler files (one per action type)

**Handler Structure**: Each handler file (e.g., `1_open_multinetwork_instructions_page.py`) contains:
1. `action()` - Executes the action
2. `verifier()` - Verifies the action completed successfully
3. `error_handler()` - Handles errors specific to that action

**Helpers Folder** (`helpers/`): Utility modules used by handlers
- `actions.py`: Low-level automation functions (typing, clicking, key presses)
- `verification_utils.py`: Text similarity, OCR extraction helpers
- `computer_vision_utils.py`: Template matching, screenshot utilities
- `ocr_utils.py`: Text recognition utilities
- `table_utils.py`: Table detection and processing

## Execution Flow

1. **Entry Point** (`process_input.py`):
   ```
   process_input_workflow() → Planning → Execution → Summary (all integrated)
   ```

2. **Planning Phase** (`workflow_planner.py`):
   ```
   Objectives → Load Definitions → Merge Parameters → Prepared Objectives
   ```

3. **Execution Phase** (`workflow_executor.py`):
   ```
   execute_workflow():
     For each objective:
       execute_single_objective()
         For each instruction:
           execute_single_instruction()
             unified_executor.execute_action_with_verification()
               ↓
             1. Load handler module (from action_list.json)
             2. Execute action (handler.action())
             3. Verify completion (handler.verifier())
             4. Handle errors if needed (handler.error_handler())
             5. Retry on failure (up to max_retries)
   ```

4. **Summary Phase** (integrated in `process_input_workflow()`):
   ```
   Prints execution summary inline → Display results
   ```

5. **Handler Execution** (individual handler files):
   ```
   action(**params) → verifier(**params) → error_handler() if failed
   ```

## Usage

### From main.py:
```python
from src.workflow_module.engine_1.process_input import process_input_workflow

success, results = process_input_workflow(
    parser_results=parser_results,
    expected_page_text="Multinetwork Instructions",
    max_retries=3
)
```

### Adding New Actions:

1. Create new handler file: `actions_2/handlers/11_new_action.py`
   ```python
   def action(**kwargs) -> Tuple[bool, str]:
       # Implement action logic
       pass
   
   def verifier(**kwargs) -> Tuple[bool, str, Optional[Dict]]:
       # Implement verification logic
       pass
   
   def error_handler(error_msg, attempt, max_attempts, **kwargs) -> Tuple[bool, str]:
       # Implement error handling logic
       pass
   ```

2. Add entry to `action_list.json`:
   ```json
   {
     "new_action_type": {
       "module": "src.workflow_module.actions_2.handlers.11_new_action",
       "description": "Description of the action",
       "has_verifier": true,
       "has_error_handler": true
     }
   }
   ```

3. Create objective definition JSON in `objective_definitions/`:
   ```json
   {
     "objective_type": "new_objective",
     "instructions": [
       {
         "action_type": "new_action_type",
         "description": "Action description",
         "parameters": {...}
       }
     ]
   }
   ```

## Key Design Principles

1. **Unified Execution**: Action execution, verification, and error handling in one flow
2. **Modular Handlers**: Each action type has its own self-contained handler file
3. **Configuration-Driven**: Handler mapping via JSON configuration
4. **Retry Logic**: Built-in retry mechanism with customizable error handlers
5. **Separation of Concerns**: 
   - Engine handles orchestration
   - Handlers handle specific actions
   - Utilities provide reusable functionality

## Benefits

- ✅ **Clear Organization**: Engine and actions are separate
- ✅ **Easy to Maintain**: One file per action type
- ✅ **Easy to Extend**: Add new actions by creating handler files
- ✅ **Integrated Verification**: Actions automatically verified
- ✅ **Smart Error Handling**: Per-action error recovery strategies
- ✅ **No Code Duplication**: Shared utilities in one place

## Version History

- **v1.0.0**: Initial refactored structure with engine and action_module separation
- **v2.0.0**: Organized folder structure with helpers subfolder
- **v3.0.0**: Separated process_input and workflow_executor
- **v4.0.0**: Removed __init__.py files, integrated summary into process_input_workflow()
- **v5.0.0**: Current version - renamed folders to `engine_1` and `actions_2` for better organization and valid Python module names

