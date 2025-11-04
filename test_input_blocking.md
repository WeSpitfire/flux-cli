# Input Blocking Test Plan

## Test Cases

### 1. Normal Operation
**Steps:**
1. Start Flux: `venv/bin/flux`
2. Type a simple query: "what files are in flux/core?"
3. Wait for response to complete
4. Verify you can type the next command

**Expected:** ✅ Normal operation, no blocking

---

### 2. Mid-Stream Input Attempt
**Steps:**
1. Start Flux: `venv/bin/flux`
2. Type a query that triggers LLM: "explain the CLI architecture"
3. While LLM is streaming response, try to type another command
4. Observe the blocking message

**Expected:** 
- ⏳ Message appears: "Please wait for current operation to complete, or press Ctrl+C to cancel"
- Input is blocked until processing completes
- After completion: "✓ Ready for next command"
- Then you can type normally

---

### 3. Ctrl+C Cancellation During Streaming
**Steps:**
1. Start Flux: `venv/bin/flux`
2. Type a long query: "read all files in flux/core and explain them"
3. While LLM is streaming, press Ctrl+C
4. Observe cancellation

**Expected:**
- ⏹️ Message appears: "Operation cancelled"
- Processing stops immediately
- You can type the next command
- Flux doesn't exit

---

### 4. Ctrl+C Exit When Idle
**Steps:**
1. Start Flux: `venv/bin/flux`
2. At the prompt (when NOT processing), press Ctrl+C
3. Observe exit behavior

**Expected:**
- "Goodbye!" message
- Flux exits cleanly

---

### 5. Mid-Tool-Execution Cancellation
**Steps:**
1. Start Flux: `venv/bin/flux`
2. Type: "create 5 new test files with content"
3. While tools are executing (after streaming ends), press Ctrl+C
4. Observe partial execution stop

**Expected:**
- Current tool finishes
- Remaining tools cancelled
- Message: "Remaining tool executions cancelled"

---

## Manual Testing Commands

```bash
# Test 1: Quick command (shouldn't block)
venv/bin/flux
> /help
> exit

# Test 2 & 3: Try to interrupt
venv/bin/flux
> read flux/ui/cli.py and explain the architecture
# (try typing another command mid-stream)
# (then Ctrl+C to cancel)
> exit

# Test 4: Ctrl+C when idle
venv/bin/flux
> [press Ctrl+C immediately at prompt]

# Test 5: Cancel during tool execution
venv/bin/flux
> /auto-approve
> create files test1.txt, test2.txt, test3.txt with "hello"
# (press Ctrl+C during file creation)
> exit
```

---

## Implementation Summary

### Changes Made:
1. **Added state flags** (`_llm_processing`, `_processing_cancelled`)
2. **Blocking check** in main run loop before `Prompt.ask()`
3. **Visual feedback** with ⏳ and ✓ indicators
4. **Ctrl+C handling** distinguishes between idle vs processing
5. **Cancellation checks** in streaming loop and tool execution
6. **Clean wrappers** for both normal and orchestrator paths

### Files Modified:
- `flux/ui/cli.py`
  - Lines 171-173: State initialization
  - Lines 284-292: Input blocking check
  - Lines 1048-1058: Ctrl+C handling
  - Lines 1246-1260: Normal query wrapper
  - Lines 1078-1097: Orchestrator wrapper
  - Lines 1315-1318: Streaming cancellation check
  - Lines 1368-1384: Tool execution cancellation checks
