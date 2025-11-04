# Test: /clear Command Implementation

## Date: 2025-11-01
## Test Type: Dogfooding validation of editing strategy improvements

## Objective
Have Flux implement a `/clear` command to test if the editing strategy improvements work in practice.

## Requirements

### Functional Requirements:
1. Add `/clear` command that clears conversation history
2. Reset LLM conversation state
3. Keep session/workspace state intact (only clear chat history)
4. Show confirmation message to user
5. Update help text with new command

### Implementation Requirements:
1. Add command handler in `flux/ui/cli.py` (similar to other commands)
2. Call appropriate LLM method to clear history
3. Add to help text in alphabetical/logical order
4. Follow existing code patterns

## Success Criteria

### Behavioral (testing our improvements):
- ✅ Flux reads files BEFORE editing
- ✅ Flux uses `edit_file` (not `ast_edit` for modifications)
- ✅ Flux makes targeted, minimal changes
- ✅ Flux succeeds within 2 attempts
- ✅ Flux verifies syntax after changes

### Functional:
- ✅ `/clear` command exists and is recognized
- ✅ Conversation history is actually cleared
- ✅ Help text includes `/clear`
- ✅ No syntax errors introduced
- ✅ Follows existing code patterns

## Expected Implementation

### Files to modify:
1. `flux/ui/cli.py` - Add command handler and help text

### Approximate changes:
- Add 3-4 lines for command handler
- Add 1 line to help text
- Possibly add method to clear LLM history (if doesn't exist)

## Comparison with /stats Failure

### What went wrong with /stats:
- ❌ Flux tried `ast_edit` without reading file
- ❌ Made 6+ failed attempts with syntax errors
- ❌ Kept retrying same approach
- ❌ Never verified changes

### What should happen with /clear:
- ✅ Flux reads cli.py first
- ✅ Uses `edit_file` for modifications
- ✅ Succeeds in 1-2 attempts
- ✅ Verifies syntax

## Metrics to Track

1. **Number of attempts**: Should be ≤2
2. **Tool selection**: Should use `read_files` then `edit_file`
3. **File reads before edits**: Should be 100%
4. **Syntax errors**: Should be 0
5. **Time to completion**: Should be <2 minutes

## Test Execution

Run Flux with the prompt:
```
Add a /clear command that clears the conversation history and resets the chat.
The command should:
- Clear the LLM conversation state
- Keep workspace/session data intact
- Show a confirmation message
- Be added to the help text
```

## Results
_To be filled after test execution_

- Attempts: __
- Tools used: __
- Success: Yes/No
- Time: __
- Notes: __
