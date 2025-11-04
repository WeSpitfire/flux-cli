# Flux Model Selection Guide

Choosing the right AI model for your workflow.

---

## Quick Recommendations

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| Quick file edits | **Haiku** | Fast, cost-effective |
| Most development work | **Sonnet** | Best balance of speed/quality |
| Complex refactoring | **Sonnet** | Large context, reliable |
| Architectural decisions | **Opus** | Highest reasoning quality |
| Multi-file changes | **Sonnet** or **Opus** | Need large context |
| Learning/Experimenting | **Haiku** | Cheapest option |

---

## Model Comparison

### Claude 3.5 Haiku
**Context**: 8K tokens  
**Speed**: ⚡⚡⚡ Very Fast  
**Cost**: 💰 $0.25/M input, $1.25/M output  
**Best for**: Quick edits, simple questions, single-file changes

**✅ Use Haiku for:**
- Editing a single file (< 200 lines)
- Quick bug fixes
- Simple refactoring
- Answering code questions
- Fast iteration

**❌ Avoid Haiku for:**
- Multi-file refactoring
- Large file edits (> 500 lines)
- Complex architectural changes
- Long conversation sessions
- Projects with many dependencies

**Flux Optimizations for Haiku:**
- Auto-clears context at 90% (invisible)
- Only 3K token history (vs 8K for Sonnet)
- Concise system prompt (saves ~500 tokens)
- No ast_edit tool (high failure rate)
- Strict workflow enforcement
- More aggressive pruning

**Tips:**
- Use `/analyze` for large files first
- Keep changes small (3-10 lines)
- Let Flux auto-manage context
- Use `/task` to maintain context across clears

---

### Claude 3.5 Sonnet
**Context**: 200K tokens  
**Speed**: ⚡⚡ Fast  
**Cost**: 💰💰 $3/M input, $15/M output  
**Best for**: Most professional development work

**✅ Use Sonnet for:**
- Multi-file refactoring
- Complex bug fixes
- Feature implementation
- Code reviews
- Test writing
- Documentation generation
- Most day-to-day development

**❌ Avoid Sonnet for:**
- Budget-constrained rapid experimentation (use Haiku)
- When you need absolute highest quality (use Opus)

**Flux Optimizations for Sonnet:**
- Full context window (200K)
- 8K token history
- Complete system prompt
- All tools available (including ast_edit)
- Generous pruning thresholds

**Tips:**
- This is the "default" model for serious work
- Can handle long conversation sessions
- Good balance of speed and quality
- Reliable for production code

---

### Claude 3 Opus
**Context**: 200K tokens  
**Speed**: ⚡ Slower  
**Cost**: 💰💰💰 $15/M input, $75/M output  
**Best for**: Highest quality reasoning, critical decisions

**✅ Use Opus for:**
- Architectural decisions
- Complex algorithm design
- Security-critical code
- Performance optimization
- Code that needs to be perfect first time
- Debugging really tricky issues

**❌ Avoid Opus for:**
- Quick edits (use Haiku)
- Routine development (use Sonnet)
- Budget-constrained projects
- Rapid iteration

**Flux Optimizations for Opus:**
- Extra-large context window
- 10K token history (vs 8K for Sonnet)
- Full system prompt
- All tools available

**Tips:**
- Use sparingly due to cost
- Perfect for code reviews before production
- Great for "getting it right the first time"
- Consider for greenfield architecture

---

### OpenAI GPT-4o
**Context**: 128K tokens  
**Speed**: ⚡⚡ Fast  
**Cost**: 💰💰 $2.50/M input, $10/M output  
**Best for**: Alternative to Sonnet, some prefer GPT-4o's style

**✅ Use GPT-4o for:**
- Similar use cases as Sonnet
- If you prefer OpenAI's response style
- Good code generation
- Multi-language support

**❌ Avoid GPT-4o for:**
- Smaller context than Claude Sonnet
- May not follow instructions as precisely

**Tips:**
- Good Sonnet alternative
- Different "personality" - try both
- Sometimes better for certain languages

---

### OpenAI GPT-3.5 Turbo
**Context**: 16K tokens  
**Speed**: ⚡⚡⚡ Very Fast  
**Cost**: 💰 $0.50/M input, $1.50/M output  
**Best for**: Budget alternative to Haiku

**✅ Use GPT-3.5 for:**
- Similar use cases as Haiku
- Slightly larger context than Haiku
- Quick questions and edits

**❌ Avoid GPT-3.5 for:**
- Quality not as high as GPT-4o/Claude
- Complex reasoning tasks
- Multi-file changes

**Flux Optimizations for GPT-3.5:**
- Same optimizations as Haiku
- Concise system prompt
- Auto-context management

---

## Switching Models

### Change Model Temporarily
```bash
export FLUX_MODEL="claude-3-5-sonnet-20241022"
flux
```

### Change Model Permanently
Edit `.env` file:
```bash
FLUX_MODEL=claude-3-5-sonnet-20241022
```

### Available Model Names

**Claude (Anthropic)**:
- `claude-3-5-sonnet-20241022` (Latest Sonnet - recommended)
- `claude-3-5-sonnet-20240620` (Older Sonnet)
- `claude-3-haiku-20240307`
- `claude-3-opus-20240229`

**OpenAI**:
- `gpt-4o` (Latest - recommended)
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`

---

## Cost Comparison

### Example: Editing a 500-line file

**Haiku**:
- Input: ~2K tokens ($0.0005)
- Output: ~500 tokens ($0.000625)
- **Total: ~$0.001** ✅ Cheapest

**Sonnet**:
- Input: ~2K tokens ($0.006)
- Output: ~500 tokens ($0.0075)
- **Total: ~$0.014** 💰 14x more than Haiku

**Opus**:
- Input: ~2K tokens ($0.03)
- Output: ~500 tokens ($0.0375)
- **Total: ~$0.068** 💰💰 68x more than Haiku

### Monthly Usage Estimates

**Light User** (10 edits/day):
- Haiku: ~$3/month
- Sonnet: ~$40/month  
- Opus: ~$200/month

**Heavy User** (50 edits/day):
- Haiku: ~$15/month
- Sonnet: ~$200/month
- Opus: ~$1000/month

---

## Model Selection Flowchart

```
Need to edit code?
│
├─ Single file < 200 lines?
│  └─ YES → Haiku ✅
│
├─ Multiple files or complex refactoring?
│  ├─ Production code, needs to be right?
│  │  └─ Opus 💎
│  └─ Regular development?
│     └─ Sonnet ⚡
│
├─ Just asking questions?
│  └─ Haiku ✅
│
└─ Architectural decisions?
   └─ Opus 💎
```

---

## Real-World Examples

### Scenario 1: Fix a Bug
**File**: `auth.py` (150 lines)  
**Task**: Fix password validation bug  
**Recommended**: **Haiku**  
**Why**: Single file, clear task, fast feedback loop  
**Cost**: ~$0.001

### Scenario 2: Add Feature
**Files**: `api/routes.py`, `api/handlers.py`, `tests/test_api.py` (800 lines total)  
**Task**: Add new API endpoint with tests  
**Recommended**: **Sonnet**  
**Why**: Multiple files, needs context across codebase  
**Cost**: ~$0.03

### Scenario 3: Refactor Architecture
**Files**: 15+ files across project  
**Task**: Refactor authentication system  
**Recommended**: **Sonnet** or **Opus**  
**Why**: Complex, needs deep understanding, can't fail  
**Cost**: Sonnet ~$0.20, Opus ~$1.00

### Scenario 4: Code Review
**Files**: 5 changed files  
**Task**: Review PR before merging to production  
**Recommended**: **Opus**  
**Why**: Need highest quality review, cost justified  
**Cost**: ~$0.15

---

## Tips for Each Model

### Maximizing Haiku:
1. **Break work into small chunks** - One file at a time
2. **Use `/analyze`** - Understand large files before editing
3. **Let it auto-clear** - Don't fight context management
4. **Use `/task`** - Maintain context across clears
5. **Quick iterations** - Fast feedback loop is Haiku's strength

### Maximizing Sonnet:
1. **Batch related changes** - Edit multiple related files together
2. **Use full context** - Don't artificially limit scope
3. **Complex refactoring** - Sonnet shines here
4. **Test generation** - Great at writing comprehensive tests
5. **Code reviews** - Excellent quality/cost ratio

### Maximizing Opus:
1. **Use sparingly** - Reserve for critical decisions
2. **Architecture work** - Best ROI for design decisions
3. **Security reviews** - Worth the cost for security-critical code
4. **Learning complex codebases** - Deep analysis capabilities
5. **Final review** - Before major releases

---

## Common Questions

### "Should I use Haiku or Sonnet for day-to-day work?"
**Sonnet**. Haiku is great for quick edits, but Sonnet is more reliable for professional development. The extra cost is usually worth it for reduced frustration and fewer errors.

### "Why does Haiku fail more often?"
Haiku has 8K context vs Sonnet's 200K. With system prompt, tool schemas, and conversation history, Haiku runs out of space quickly. Flux auto-manages this, but some tasks just need more context.

### "Can I mix models in one session?"
No, but you can start a new session with a different model. Use `/session save` to checkpoint, switch models, and continue.

### "Which is better: GPT-4o or Sonnet?"
**Try both**. They have different "personalities". Some users prefer GPT-4o's responses, others prefer Sonnet's. Performance is similar, so it's personal preference.

### "Is Opus worth 5x the cost of Sonnet?"
For **critical code** and **architectural decisions**, yes. For routine development, no. Use Sonnet for 95% of work, Opus for the 5% that really matters.

---

## Conclusion

**Start with Sonnet** for most work. It's the best balance of quality, speed, and cost.

**Use Haiku** when:
- You're experimenting and iterating quickly
- Budget is very constrained  
- Tasks are simple and single-file

**Use Opus** when:
- Code is security-critical
- Making important architectural decisions
- You need the absolute best quality

**Remember**: Flux is optimized for all models. Haiku gets auto-context management, Sonnet gets full power, and Opus gets maximum quality. Choose based on your task, not because one model is "better".
