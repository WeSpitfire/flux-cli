# Flux User Testing Guide

**Version:** 1.0  
**Date:** Day 22 of 30  
**Status:** Ready for Testing

---

## Overview

This guide outlines the complete user testing process for Flux, including recruitment, testing protocol, feedback collection, and analysis.

**Goal:** Validate Flux with real users before launch

---

## Table of Contents

1. [Test Participant Criteria](#test-participant-criteria)
2. [Testing Protocol](#testing-protocol)
3. [Test Scenarios](#test-scenarios)
4. [Feedback Collection](#feedback-collection)
5. [Bug Reporting](#bug-reporting)
6. [Success Metrics](#success-metrics)
7. [Analysis Framework](#analysis-framework)

---

## Test Participant Criteria

### Target Participants: 5-10 Developers

#### Experience Levels
- **2-3 Junior Developers** (0-2 years experience)
- **3-4 Mid-Level Developers** (3-5 years experience)
- **1-2 Senior Developers** (5+ years experience)

#### Technical Background
- ✅ Comfortable with command line
- ✅ Uses terminal daily
- ✅ Familiar with Git and npm
- ✅ Experience with CI/CD workflows
- ✅ Bonus: Used Warp or other modern terminals

#### Operating Systems
- **3-4 participants:** macOS
- **2-3 participants:** Windows
- **1-2 participants:** Linux

#### Current Tool Usage
- Ask what terminal they currently use
- What features they love/hate
- Pain points in daily workflow
- What they wish existed

---

## Testing Protocol

### Session Structure (60 minutes)

#### Part 1: Introduction (5 minutes)
1. Welcome and thank participant
2. Explain Flux's purpose
3. Outline testing process
4. Emphasize: We're testing the product, not you!
5. Ask permission to record (optional)

#### Part 2: Onboarding (10 minutes)
**Task:** First-time user experience

**Observe:**
- Can they open Flux?
- Do they understand the interface?
- Can they find features?
- Do they read the welcome screen?
- What's their first reaction?

**Questions:**
- "What do you think Flux does?"
- "What would you try first?"
- "Is anything confusing?"

#### Part 3: Guided Tasks (25 minutes)
**Complete 5 core scenarios** (see Test Scenarios below)

For each task:
1. Give clear goal (not instructions)
2. Ask them to think aloud
3. Observe without helping
4. Note difficulties and questions
5. Time to completion

#### Part 4: Free Exploration (10 minutes)
**Task:** "Use Flux however you want"

**Observe:**
- What features do they explore?
- What do they try to do?
- What delights them?
- What frustrates them?

#### Part 5: Feedback (10 minutes)
**Structured interview** (see Feedback Collection)

---

## Test Scenarios

### Scenario 1: Command Palette Basics ⌨️

**Goal:** "Find and use the command palette"

**Success Criteria:**
- Opens command palette (Cmd+K)
- Searches for a command
- Executes a command
- Understands keyboard navigation

**Observe:**
- Do they discover the shortcut?
- Is the search intuitive?
- Do they understand results?
- Any confusion?

**Time Target:** 2 minutes

---

### Scenario 2: Command Intelligence 🧠

**Goal:** "Try to run a risky command and see what happens"

**Example Commands:**
```bash
rm -rf /
sudo rm -rf /var
git push --force origin main
npm publish --force
```

**Success Criteria:**
- Flux detects the risk
- Warning dialog appears
- User understands the risk
- Can confirm or cancel

**Observe:**
- Do they notice the warning?
- Do they read it?
- Do they understand severity?
- Do they feel protected?

**Time Target:** 3 minutes

---

### Scenario 3: Create a Workflow 🔄

**Goal:** "Automate your Git commit & push process"

**Expected Steps:**
1. Open workflow manager
2. Create new workflow
3. Add steps (git add, commit, push)
4. Add variable for commit message
5. Save workflow
6. Run workflow

**Success Criteria:**
- Can find workflow manager
- Understands step editor
- Can add variables
- Workflow executes successfully

**Observe:**
- Is the UI intuitive?
- Do they understand step types?
- Can they add variables?
- Any confusion in the flow?

**Time Target:** 8 minutes

---

### Scenario 4: Browse & Run Workflows 📚

**Goal:** "Find and run a pre-made workflow"

**Steps:**
1. Open workflow library
2. Browse available workflows
3. Search for "Deploy"
4. Run "Deploy to Production" workflow
5. Provide required inputs
6. Watch execution

**Success Criteria:**
- Can navigate library
- Search works well
- Understands workflow details
- Can provide inputs
- Execution is clear

**Observe:**
- Is the library browsable?
- Is search helpful?
- Do they understand variables?
- Is progress clear?

**Time Target:** 5 minutes

---

### Scenario 5: Keyboard Shortcuts 🎹

**Goal:** "Discover and use keyboard shortcuts"

**Tasks:**
- Open shortcuts overlay (Cmd+/)
- Try 3 different shortcuts
- Navigate workflow manager with keyboard
- Use arrow keys in lists

**Success Criteria:**
- Finds shortcut overlay
- Understands shortcut format
- Can execute shortcuts
- Keyboard navigation works

**Observe:**
- Is Cmd+/ discoverable?
- Are shortcuts memorable?
- Does navigation feel natural?
- Any conflicts?

**Time Target:** 4 minutes

---

### Scenario 6: Performance & Responsiveness ⚡

**Goal:** "Stress test Flux with lots of data"

**Tasks:**
- Search through 100+ items
- Open large workflow editor
- Rapid typing in search
- Scroll long lists
- Switch between features quickly

**Success Criteria:**
- No lag or jank
- Search is instant
- Smooth scrolling
- Fast transitions

**Observe:**
- Any performance issues?
- UI responsiveness
- Loading states
- Memory usage

**Time Target:** 3 minutes

---

## Feedback Collection

### Post-Test Survey

#### Section 1: First Impressions
1. **Visual Appeal** (1-5 stars)
   - "How visually appealing is Flux?"
   - Comments: _______________

2. **Clarity** (1-5 stars)
   - "How clear was the purpose of Flux?"
   - Comments: _______________

3. **Ease of Use** (1-5 stars)
   - "How easy was Flux to use?"
   - Comments: _______________

#### Section 2: Feature Ratings

Rate each feature (1-5 stars):

- **Command Palette**
  - Usefulness: ⭐⭐⭐⭐⭐
  - Ease of use: ⭐⭐⭐⭐⭐
  - Comments: _______________

- **Command Intelligence**
  - Usefulness: ⭐⭐⭐⭐⭐
  - Accuracy: ⭐⭐⭐⭐⭐
  - Comments: _______________

- **Workflow Automation**
  - Usefulness: ⭐⭐⭐⭐⭐
  - Ease of use: ⭐⭐⭐⭐⭐
  - Comments: _______________

- **Keyboard Shortcuts**
  - Discoverability: ⭐⭐⭐⭐⭐
  - Memorability: ⭐⭐⭐⭐⭐
  - Comments: _______________

#### Section 3: Comparison

**Current Terminal:**
- What terminal do you use now? _______________
- What do you love about it? _______________
- What do you hate about it? _______________

**Flux vs Current:**
- Would you switch to Flux? ☐ Yes ☐ Maybe ☐ No
- Why or why not? _______________
- What would convince you? _______________

#### Section 4: Open Feedback

**What you loved:**
- _______________
- _______________
- _______________

**What you hated:**
- _______________
- _______________
- _______________

**What's missing:**
- _______________
- _______________
- _______________

**Bugs encountered:**
- _______________
- _______________
- _______________

#### Section 5: Likelihood Scores

1. **Net Promoter Score (NPS)**
   "How likely are you to recommend Flux to a colleague?"
   0 1 2 3 4 5 6 7 8 9 10

2. **Daily Use**
   "How likely would you use Flux daily?"
   0 1 2 3 4 5 6 7 8 9 10

3. **Pay for It**
   "If Flux cost $29, would you buy it?"
   ☐ Yes ☐ Maybe ☐ No

---

## Bug Reporting

### Bug Report Template

```markdown
**Bug Title:** [Short description]

**Severity:** 
☐ Critical (Crash/Data loss)
☐ High (Broken feature)
☐ Medium (Annoying but workaround exists)
☐ Low (Cosmetic/Minor)

**Description:**
[What happened vs what should happen]

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [Result]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happened]

**Environment:**
- OS: [macOS/Windows/Linux]
- Browser: [Chrome/Firefox/Safari]
- Version: [e.g. Chrome 120]

**Screenshots/Video:**
[Attach if available]

**Additional Context:**
[Any other relevant information]
```

### Bug Priority Matrix

| Severity | Frequency | Priority |
|----------|-----------|----------|
| Critical | Common | **P0** - Fix immediately |
| Critical | Rare | **P1** - Fix before launch |
| High | Common | **P1** - Fix before launch |
| High | Rare | **P2** - Fix soon |
| Medium | Common | **P2** - Fix soon |
| Medium | Rare | **P3** - Backlog |
| Low | Any | **P3** - Backlog |

---

## Success Metrics

### Quantitative Metrics

#### Task Success Rate
- **Target:** >80% task completion
- **Measure:** Participants who complete each scenario

#### Time on Task
- **Target:** Complete scenarios within time targets
- **Measure:** Average time per scenario

#### Error Rate
- **Target:** <2 errors per scenario
- **Measure:** Number of mistakes/wrong paths

#### System Usability Scale (SUS)
- **Target:** Score >68 (above average)
- **Measure:** 10-question SUS survey

#### Net Promoter Score (NPS)
- **Target:** >30 (good)
- **Measure:** 0-10 likelihood to recommend

### Qualitative Metrics

#### Satisfaction
- Overall happiness with Flux
- Feature-specific satisfaction
- Comparison to current tools

#### Ease of Use
- Learnability
- Efficiency
- Memorability
- Error prevention/recovery
- Satisfaction

#### Pain Points
- What frustrated users?
- Where did they get stuck?
- What was confusing?
- What was missing?

#### Delighters
- What exceeded expectations?
- What made them smile?
- What would they tell friends?

---

## Analysis Framework

### Data Collection

#### During Testing
- Screen recording (with permission)
- Note-taking (observer)
- Think-aloud audio
- Time tracking
- Error logging

#### After Testing
- Survey responses
- Bug reports
- Feature requests
- Quotes and testimonials

### Analysis Process

#### Step 1: Consolidate Data (1 hour)
- Gather all recordings
- Compile survey responses
- List all bugs
- Organize feedback

#### Step 2: Identify Patterns (2 hours)
**Questions to ask:**
- What did multiple users struggle with?
- What features were loved?
- What features were ignored?
- Common complaints?
- Unexpected behaviors?

#### Step 3: Prioritize Issues (1 hour)
**Priority Framework:**

**Must Fix (P0/P1):**
- Blocks core functionality
- Affects >50% of users
- Critical bugs
- Major UX issues

**Should Fix (P2):**
- Affects 20-50% of users
- Medium bugs
- Nice-to-have UX improvements

**Could Fix (P3):**
- Affects <20% of users
- Low priority bugs
- Polish items

#### Step 4: Create Action Plan (1 hour)
For each P0/P1 issue:
1. Root cause
2. Proposed solution
3. Estimated effort
4. Owner
5. Deadline

#### Step 5: Report (30 minutes)
**Summary Document:**
- Executive summary
- Key findings
- Metrics & scores
- Priority issues
- Recommendations
- Next steps

---

## Testing Best Practices

### Do's ✅

1. **Stay Silent**
   - Let users struggle
   - Don't lead them
   - Resist urge to help

2. **Ask "Why?"**
   - Dig deeper on feedback
   - Understand motivations
   - Get to root causes

3. **Observe Body Language**
   - Confusion = furrowed brow
   - Frustration = sighs
   - Delight = smiles
   - Boredom = checking phone

4. **Take Notes**
   - Write down quotes
   - Note timestamps
   - Log errors
   - Capture insights

5. **Thank Participants**
   - Show gratitude
   - Offer compensation
   - Share results (if appropriate)

### Don'ts ❌

1. **Don't Defend**
   - Criticism is gift
   - Don't explain why
   - Accept feedback

2. **Don't Lead**
   - Avoid "Did you see...?"
   - Let them discover
   - Use open questions

3. **Don't Interrupt**
   - Let them finish
   - Wait for pauses
   - Be patient

4. **Don't Test Multiple Changes**
   - One major change at a time
   - Keep version consistent
   - Track versions

5. **Don't Ignore Edge Cases**
   - Weird bugs matter
   - Document everything
   - Follow up if needed

---

## Participant Recruitment

### Where to Find Testers

#### Online Communities
- Twitter/X (#webdev, #devtools)
- Reddit (r/webdev, r/programming)
- Discord servers (developer communities)
- LinkedIn groups

#### Your Network
- Colleagues
- Former coworkers
- Meetup attendees
- Open source contributors

#### Platforms
- UserTesting.com
- Respondent.io
- BetaList
- Product Hunt

### Recruitment Message Template

```
Subject: Help test Flux - A modern terminal (60 min, $50 gift card)

Hi [Name],

I'm building Flux, a terminal that has your back. It features:
- Smart command intelligence (warns about risky commands)
- Powerful workflow automation
- Beautiful, modern UI

I'm looking for developers to test Flux and provide feedback.

Details:
- 60-minute session (video call or in-person)
- Test Flux features and share thoughts
- $50 Amazon gift card as thanks
- [Date/Time options]

Interested? Reply and I'll send details!

Thanks,
[Your Name]
```

---

## Session Checklist

### Before Session
- [ ] Flux is running and tested
- [ ] Screen recording ready
- [ ] Survey forms printed/ready
- [ ] Note-taking setup
- [ ] Participant confirmed
- [ ] Incentive ready (gift card)

### During Session
- [ ] Welcome participant
- [ ] Get recording consent
- [ ] Explain process
- [ ] Start recording
- [ ] Take notes
- [ ] Stay silent
- [ ] Observe body language
- [ ] Ask follow-up questions

### After Session
- [ ] Stop recording
- [ ] Complete survey
- [ ] Collect bug reports
- [ ] Thank participant
- [ ] Give incentive
- [ ] Back up recording
- [ ] Write summary notes
- [ ] Log key insights

---

## Example Questions

### Onboarding
- "What's your first impression?"
- "What do you think this does?"
- "Where would you start?"

### During Tasks
- "What are you thinking?"
- "What are you looking for?"
- "What would you expect to happen?"

### When Stuck
- "What would you try next?"
- "What would make this easier?"
- "What information do you need?"

### After Tasks
- "How did that feel?"
- "What was confusing?"
- "What did you like?"

### Comparison
- "How does this compare to [current tool]?"
- "What would make you switch?"
- "What's missing?"

---

## Expected Findings

### Likely Positive Feedback
- Beautiful, modern UI
- Smart command warnings
- Workflow automation is powerful
- Keyboard shortcuts are handy
- Performance is excellent

### Likely Issues to Find
- Onboarding could be clearer
- Some shortcuts not discoverable
- Workflow editor has learning curve
- Need more example workflows
- Documentation gaps

### Likely Feature Requests
- More integrations (GitHub, Docker, etc.)
- Custom themes
- Terminal emulation
- Plugin system
- Team/sync features

---

## Timeline

### Week 1: Preparation
- **Day 1-2:** Recruit participants
- **Day 3:** Finalize test plan
- **Day 4:** Practice sessions
- **Day 5:** Confirm schedules

### Week 2: Testing
- **Day 1-3:** Conduct 5-10 sessions
- **Day 4:** Buffer for rescheduling
- **Day 5:** Final sessions

### Week 3: Analysis
- **Day 1-2:** Analyze data
- **Day 3:** Create action plan
- **Day 4:** Prioritize fixes
- **Day 5:** Write report

---

## Incentives

### Gift Cards ($50 each)
- Amazon (universal)
- Coffee shops (Starbucks)
- Tech stores (Apple, Best Buy)
- Food delivery (Uber Eats, DoorDash)

### Alternative Incentives
- Early access to Flux
- Lifetime Pro license
- Name in credits
- Shoutout on social media
- Contribution to charity

---

## Legal & Ethics

### Consent Form

```
USER TESTING CONSENT FORM

I agree to participate in user testing for Flux.

I understand:
- My session may be recorded (video/audio)
- Recordings are for research only
- My feedback will be used to improve Flux
- I can stop at any time
- My identity will be kept confidential

I consent to:
- [ ] Video recording
- [ ] Audio recording
- [ ] Screen recording
- [ ] Note-taking

Signature: _______________
Date: _______________
```

### Privacy
- Store data securely
- Anonymize quotes
- Don't share personal info
- Delete recordings after analysis (unless consent given)

---

## Success Definition

### Flux is ready for launch if:

✅ **>80% task completion rate**  
✅ **SUS score >68**  
✅ **NPS >30**  
✅ **<5 P0/P1 bugs**  
✅ **>70% would use daily**  
✅ **Overall satisfaction >4/5**

### Red Flags (Don't launch if):

🚨 **<50% task completion**  
🚨 **Multiple P0 bugs**  
🚨 **Consistent confusion on core features**  
🚨 **Users wouldn't switch from current tool**  
🚨 **Significant performance issues**

---

## Resources

### Templates
- [ ] Recruitment email
- [ ] Consent form
- [ ] Survey form
- [ ] Bug report template
- [ ] Session checklist
- [ ] Note-taking template

### Tools
- Screen recording: QuickTime, OBS
- Surveys: Google Forms, Typeform
- Video calls: Zoom, Google Meet
- Note-taking: Notion, Evernote
- Analysis: Excel, Sheets

---

## Next Steps After Testing

### Immediate (Days 23-24)
1. Fix all P0/P1 bugs
2. Address major UX issues
3. Add missing critical features

### Short-term (Days 25-27)
1. Fix P2 bugs
2. Improve onboarding
3. Add requested features
4. Write documentation

### Long-term (Post-launch)
1. Fix P3 bugs
2. Build feature requests
3. Continuous improvement
4. Regular user testing

---

**Ready to test? Let's validate Flux with real users!** 🧪✨

*Last updated: Day 22 of 30*
