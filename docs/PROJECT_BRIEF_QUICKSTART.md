# Project Brief - Quick Start Guide

## What is Project Brief?

Project Brief is Flux's solution to the "AI forgetting" problem. It ensures that critical information like constraints, coding conventions, and project context is **ALWAYS** in the AI's prompt and **NEVER** forgotten, even after 100+ messages or terminal restarts.

---

## Common Problem

**Before Project Brief:**
```
You: Never use AWS, we use Digital Ocean
Flux: Got it!

[20 messages later...]

You: How should I deploy this?
Flux: I recommend using AWS Lambda...
You: 😤 I told you not to use AWS!
```

**With Project Brief:**
```
You: /brief-constraint Never use AWS, use Digital Ocean
Flux: ✓ Constraint added (will NEVER be forgotten)

[100+ messages later, or even after terminal restart...]

You: How should I deploy this?
Flux: Since you're using Digital Ocean (per your constraint), 
      I recommend using their App Platform...
```

---

## Quick Commands

### View Your Brief
```bash
/brief
```
Shows all constraints, coding style, and project context.

### Add a Constraint (Never Forgotten!)
```bash
/brief-constraint Never use AWS
/brief-constraint Store photos in our database, not S3
/brief-constraint Use Resend for email
```

### Add Coding Style
```bash
/brief-style Use TypeScript strict mode
/brief-style No console.log in production code
/brief-style Write tests for all features
```

### Add Project Info
```bash
/brief-add language Python
/brief-add framework Django
/brief-add database PostgreSQL
```

---

## Real-World Examples

### Example 1: Cloud Provider Preference
```bash
# Set it once
/brief-constraint Never use Amazon AWS products
/brief-constraint Use Digital Ocean for all cloud infrastructure

# Now Flux will NEVER suggest AWS, even after 100 messages
```

### Example 2: Privacy-First App
```bash
/brief-constraint All user data stored in our database
/brief-constraint Never send user info to third-party services
/brief-constraint Photos must be encrypted at rest
```

### Example 3: Code Quality Standards
```bash
/brief-style Use TypeScript strict mode, no 'any' types
/brief-style All functions must have JSDoc comments
/brief-style Run eslint before committing
```

### Example 4: Email Service
```bash
/brief-constraint Use Resend for all email sending
/brief-add description "Email provider: Resend API"
```

---

## How It Works

1. **Persistent Storage**: Brief saved to `~/.flux/projects/{project}/brief.json`
2. **Always in Prompt**: Injected into EVERY single AI request
3. **Auto-Save**: Saved after each query (survives crashes)
4. **Auto-Load**: Loaded on Flux startup (survives restarts)

---

## Best Practices

### ✅ Do This
- Add constraints at the start of your project
- Use for "never do X" rules
- Set coding conventions you want followed
- Keep constraints clear and concise

### ❌ Don't Do This
- Add temporary information (just tell Flux normally)
- Add file-specific details (brief is project-level)
- Duplicate info that's already in your code
- Over-constrain (keep it high-level)

---

## Full Example

```bash
# Start new project
cd my-app/
flux

# Set up project brief
/brief-constraint Never use AWS, use Digital Ocean
/brief-constraint Use Resend for email
/brief-constraint Store all photos in PostgreSQL
/brief-style Use TypeScript strict mode
/brief-style No console.log in production
/brief-add framework Next.js
/brief-add database PostgreSQL

# View it
/brief

# Now code normally - Flux will remember all of this!
> "Build a photo upload feature"
# Flux will use PostgreSQL for photos (not S3)
# Flux will use TypeScript strict mode
# Flux will NOT suggest AWS services
```

---

## Advanced: Manual Editing

```bash
/brief-edit
```
Opens `~/.flux/projects/{project}/brief.json` in your editor for bulk changes.

---

## Troubleshooting

**Brief not persisting?**
- Check `~/.flux/projects/{project_name}/brief.json` exists
- Verify JSON is valid

**Flux still forgetting?**
- Run `/brief` to confirm constraints are there
- Enable debug: `/debug-on` to see system prompt

**Auto-detection not working?**
- Manually add info: `/brief-add language Python`
- Check you have package.json or similar

---

## Summary

Project Brief = **Set it once, never repeat yourself**

```bash
# Three simple commands:
/brief                           # View
/brief-constraint <text>         # Add constraint
/brief-style <text>              # Add coding style

# That's it! Flux will remember forever.
```

---

For complete documentation, see `PROJECT_BRIEF_SYSTEM.md`
