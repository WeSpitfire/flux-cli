# Retry Loop Prevention - Implementation Summary

## Problem Identified

From the user's conversation log with Flux, the LLM was asking for approval **three times in a row** for the same edit operation. Analysis revealed:

1. **First attempt**: Edit failed with `SEARCH_TEXT_NOT_FOUND`, auto-read file
2. **Second attempt**: Same search text used again, failed again, auto-read again  
3. **Third attempt**: Finally adjusted search text and succeeded

The root cause: **No hard blocking mechanism** to prevent the LLM from retrying the same failed operation indefinitely.

## Improvements Implemented

### 1. **Hard Blocking After 2 Failures** ✅
**Location**: `flux/ui/cli.py:576-598`

Before executing any tool, we now check if it has failed twice:
- If yes, **block execution completely**
- Return an error with guidance for alternative approaches
- Display prominent red warning to user and LLM
- Tool is NOT executed at all

**Impact**: Forces the LLM to try a different strategy after 2 failures instead of endless retries.

### 2. **Enhanced Auto-Recovery Messaging** ✅
**Location**: `flux/ui/cli.py:604-632`

When `SEARCH_TEXT_NOT_FOUND` occurs:
- Show current retry count: "attempt 1 of 2"
- Provide **explicit step-by-step instructions** for what to do next
- Warn that next failure will be blocked
- Make it clear: "DO NOT guess - use exact content shown"

**Impact**: LLM gets much clearer guidance on exactly what it needs to do differently.

### 3. **Visual Warning on 2nd Failure** ✅
**Location**: `flux/ui/cli.py:674-683`

After recording the 2nd consecutive failure:
- Display prominent yellow warning panel
- Shows both user and LLM that retry loop is detected
- Explicitly states "next attempt will be blocked"

**Impact**: Clear visual indicator that strategy change is required.

### 4. **Aggressive Failure Reset** ✅
**Location**: `flux/ui/cli.py:691-695`

On ANY successful tool execution:
- Reset ALL failure tracking (not just for that tool)
- Show confirmation message
- Prevents stale failure state affecting new operations

**Impact**: Clean slate after success, no lingering failure state.

### 5. **Retry Context in System Prompt** ✅
**Location**: `flux/ui/cli.py:767-770, 806-826`

When continuing after tool execution:
- Inject retry warnings directly into system prompt
- Lists specific failures and alternative approaches
- Visible to LLM on every continuation

**Impact**: LLM is constantly aware of retry state during multi-turn tool execution.

## Key Changes Summary

| Change | Before | After |
|--------|--------|-------|
| **Retry limit** | None (infinite) | Hard block after 2 failures |
| **Error recovery** | Vague "retry with correct text" | Step-by-step instructions with retry count |
| **Visual feedback** | Minimal | Prominent warnings on 2nd failure and blocking |
| **Failure reset** | Per-tool only | Complete reset on success |
| **LLM awareness** | Tool result only | System prompt injection |

## Testing Recommendations

1. **Test retry blocking**:
   - Intentionally use wrong search text twice in `edit_file`
   - Verify 3rd attempt is blocked with guidance

2. **Test auto-recovery**:
   - Use wrong search text once
   - Verify clear instructions appear with retry count
   - Verify file is auto-read with helpful context

3. **Test visual warnings**:
   - Trigger 2 consecutive failures
   - Verify yellow warning panel appears

4. **Test success reset**:
   - Fail twice, then succeed
   - Verify "failure tracking reset" message
   - Verify next operation works normally

## Expected User Experience Improvement

**Before**: 
- LLM asks 3+ times for same change
- User gets frustrated
- No clear indication of what's wrong

**After**:
- LLM blocked after 2 failures
- Clear guidance on what to try instead
- Visual feedback on retry state
- Forced strategy change prevents loops

## Files Modified

- `flux/ui/cli.py` - All retry loop prevention logic

## Backward Compatibility

✅ All changes are backward compatible:
- Existing functionality unchanged
- New logic only activates on failures
- No breaking changes to tool interfaces
