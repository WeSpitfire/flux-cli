# Making Flux Smarter: A Strategy Guide

## The Problem

Flux feels "dumb" compared to Warp because it:
1. **Generates stub code** without understanding the real codebase
2. **Doesn't validate** its own implementations
3. **Breaks existing code** by replacing instead of extending
4. **Works blindly** without checking if previous steps succeeded
5. **Asks too many questions** instead of being proactive

## Root Causes

### 1. System Prompt Is Too Generic
**Current:** Generic instructions about being helpful
**Needed:** Specific instructions about codebase analysis, validation, and iterative development

### 2. No Pre-Flight Checks
Flux should ALWAYS:
- Read relevant existing code FIRST
- Understand APIs and interfaces BEFORE using them
- Check for naming conflicts BEFORE creating classes
- Validate generated code IMMEDIATELY after creation

### 3. No Self-Correction Loop
When Flux creates code, it should:
1. Generate the code
2. Read it back
3. Check if it actually works with the codebase
4. Fix any issues BEFORE asking for approval

### 4. Weak Context Awareness
Flux doesn't maintain awareness of:
- What classes/functions already exist
- What APIs are available
- What patterns the codebase uses
- What mistakes it just made

## Solutions

### CRITICAL FIX 1: Enhance System Prompt

Add to `SYSTEM_PROMPT` in `flux/llm/prompts.py`:

```python
CODEBASE_AWARENESS = """
CRITICAL RULES FOR CODE GENERATION:

1. ALWAYS READ BEFORE YOU WRITE
   - Before creating/modifying code, READ the related files first
   - Understand existing APIs, classes, and patterns
   - Check for naming conflicts and dependencies

2. VALIDATE YOUR OWN CODE
   - After generating code, READ IT BACK immediately
   - Check if methods you call actually exist
   - Verify imports are correct
   - Test logic for obvious bugs

3. EXTEND, DON'T REPLACE
   - When adding features, extend existing classes
   - Don't rename or replace existing functionality
   - Use inheritance or composition appropriately

4. BE PROACTIVE, NOT REACTIVE
   - If you need information, GET IT (read files, search code)
   - Don't ask the user questions you can answer yourself
   - Only ask when you truly need human judgment

5. ITERATE AND FIX
   - If your first attempt has issues, FIX THEM immediately
   - Don't wait for the user to point out obvious problems
   - Self-correct before presenting final code

EXAMPLE OF GOOD BEHAVIOR:
1. User asks: "Add a cache to the LLM"
2. You do:
   a. Read flux/llm/provider.py to understand current structure
   b. Search for existing cache implementations
   c. Design cache that integrates with existing patterns
   d. Create cache.py with proper integration
   e. Read back your code and verify it works
   f. Fix any issues you find
   g. Present the working solution

EXAMPLE OF BAD BEHAVIOR:
1. User asks: "Add a cache to the LLM"
2. You do:
   a. Create cache.py with stub code
   b. Call self.cache.get() without checking if it exists
   c. Present broken code and ask "what's next?"
   
DON'T BE THE BAD EXAMPLE.
"""
```

### CRITICAL FIX 2: Add Self-Validation Tool

Create `flux/tools/self_validate.py`:

```python
from typing import Dict, List
from pathlib import Path

class SelfValidationTool:
    """Tool for Flux to validate its own generated code."""
    
    def validate_code_before_approval(self, file_path: Path, dependencies: List[str]) -> Dict:
        """
        Validate generated code before showing to user.
        
        Checks:
        1. All imported modules exist
        2. All called methods exist in their classes
        3. No naming conflicts with existing code
        4. Syntax is valid
        5. Logic makes sense
        
        Returns:
            {'valid': bool, 'issues': List[str], 'fixes': List[str]}
        """
        issues = []
        fixes = []
        
        # Read the generated code
        with open(file_path) as f:
            code = f.read()
        
        # Check imports
        import_issues = self._check_imports(code, dependencies)
        issues.extend(import_issues)
        
        # Check method calls
        method_issues = self._check_method_calls(code, dependencies)
        issues.extend(method_issues)
        
        # Check naming conflicts
        conflict_issues = self._check_naming_conflicts(code)
        issues.extend(conflict_issues)
        
        # Suggest fixes
        if issues:
            fixes = self._suggest_fixes(issues)
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'fixes': fixes
        }
```

### CRITICAL FIX 3: Mandatory Read-Before-Write

Modify `flux/ui/cli.py` to ENFORCE reading before writing:

```python
class IntelligentCodeGenerator:
    """Wrapper that enforces smart code generation."""
    
    def __init__(self, cli):
        self.cli = cli
        self.context = {}  # Store what we've read
    
    async def smart_create_file(self, path: str, content: str):
        """Create file with mandatory validation."""
        
        # Step 1: Read related files FIRST
        related_files = self._find_related_files(path)
        for f in related_files:
            if f not in self.context:
                self.context[f] = await self.cli.tools.execute('read_files', paths=[f])
        
        # Step 2: Generate code (already done)
        
        # Step 3: VALIDATE before showing user
        validation = await self._validate_code(path, content)
        
        # Step 4: If invalid, FIX IT
        if not validation['valid']:
            content = await self._auto_fix_code(content, validation['fixes'])
        
        # Step 5: Only NOW show to user
        return await self.cli.tools.execute('write_file', path=path, content=content)
```

### CRITICAL FIX 4: Smarter Orchestrator

The orchestrator should be **much** smarter:

```python
class SmartOrchestrator:
    """Intelligent task orchestration with validation."""
    
    async def execute_with_validation(self, task: str):
        """Execute task with built-in validation."""
        
        # Phase 1: UNDERSTAND
        context = await self._gather_context(task)
        
        # Phase 2: PLAN
        plan = await self._create_validated_plan(task, context)
        
        # Phase 3: EXECUTE
        results = []
        for step in plan:
            result = await self._execute_step(step)
            
            # VALIDATE IMMEDIATELY
            if not result['valid']:
                # AUTO-FIX
                result = await self._fix_step(step, result)
            
            results.append(result)
        
        # Phase 4: VERIFY
        await self._verify_complete_solution(results)
        
        return results
```

### CRITICAL FIX 5: Better Tool Use Patterns

Flux needs to learn patterns like:

```python
# BAD: Blind execution
write_file('new_class.py', stub_code)

# GOOD: Intelligent execution
1. Search for similar classes
2. Read the similar classes
3. Understand the pattern
4. Generate code following the pattern
5. Validate the code
6. Fix any issues
7. Write the file
```

## Implementation Priority

### Phase 1: Quick Wins (DO NOW)
1. ✅ Enhance system prompt with codebase awareness rules
2. ✅ Add self-validation checks after code generation
3. ✅ Enforce read-before-write pattern

### Phase 2: Medium Term (NEXT WEEK)
4. Build intelligent orchestrator with validation
5. Add learning from past mistakes
6. Implement automatic fix suggestions

### Phase 3: Long Term (NEXT MONTH)
7. Train on good vs bad code generation examples
8. Build semantic code understanding
9. Add proactive refactoring suggestions

## Measuring Success

Flux is "smart" when:
- ✅ Generated code works on first try (>90% of the time)
- ✅ No obvious bugs slip through
- ✅ Code follows codebase patterns automatically
- ✅ Doesn't break existing functionality
- ✅ Asks <2 clarifying questions per task
- ✅ Self-corrects mistakes without user intervention

## Specific Fixes for Current Issue

For the self-healing system, Flux should have:

1. **Read the LLM provider code FIRST**
   ```python
   # This should have happened automatically:
   read_files(['flux/llm/base.py', 'flux/llm/openai_provider.py'])
   # THEN generate FixGenerator with correct API calls
   ```

2. **Checked for TestRunner conflicts**
   ```python
   # Before editing:
   grep_search('class TestRunner')
   # Realize it exists, create AutoTester as separate class
   ```

3. **Validated generated code**
   ```python
   # After creating fix_generator.py:
   validate_code('flux/core/fix_generator.py')
   # Catch the missing generate_fix() method
   # Fix it immediately
   ```

4. **Used proper LLM API**
   ```python
   # Instead of: fix_code, confidence = self.llm.generate_fix(prompt)
   # Should be: response = await self.llm.send_message(prompt, tools=[])
   ```

## Bottom Line

**Flux needs to think like a senior developer, not a junior intern.**

Senior developers:
- Research before implementing
- Validate their own work
- Follow existing patterns
- Fix mistakes immediately
- Ask smart questions sparingly

This is what Warp does well, and what Flux needs to learn.
