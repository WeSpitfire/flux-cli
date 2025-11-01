# Flux CLI - Quick Start

Get Flux up and running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- An Anthropic API key ([get one here](https://console.anthropic.com/))

## Setup

1. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Add your API key:**
   ```bash
   # Edit .env file
   nano .env
   
   # Add your key:
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Activate the environment:**
   ```bash
   source venv/bin/activate
   ```

## Usage

### Interactive Mode

Start Flux and have a conversation:

```bash
python flux/main.py
```

Then try:
```
You: what files are in this directory?
You: search for TODO comments in python files
You: create a hello world script in test.py
```

### Single Query Mode

Run a one-off command:

```bash
python flux/main.py "list all python files in this directory"
```

## Example Queries

### Understanding Code
```
"where is the main function defined?"
"search for error handling in *.js files"
"read the package.json file"
```

### Making Changes
```
"create a new file called utils.py with a logger function"
"add error handling to the main function in app.py"
"fix the typo in README.md where it says 'teh' instead of 'the'"
```

### Running Commands
```
"run the tests"
"what git branch am I on?"
"install the requests library"
```

## Tips

1. **Be specific**: "fix the bug in line 42 of app.py" works better than "fix bugs"
2. **Check before editing**: Flux will read files before editing them
3. **Iterative**: Ask Flux to search first, then make changes based on what it finds
4. **Use tools**: Flux will automatically use the right tools (read, write, edit, search, command)

## Testing on GSM_MIN

Navigate to your GSM_MIN directory and start Flux:

```bash
cd /Users/developer/SynologyDrive/GSM_MIN
python /Users/developer/SynologyDrive/flux-cli/flux/main.py
```

Try these queries:
```
"what is this project about?"
"find all React components"
"show me the authentication logic"
"what npm scripts are available?"
```

## Troubleshooting

**Import errors?**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**API key not found?**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Or add it to .env
```

**Tool execution fails?**
- Check that you're in the right directory
- Verify file paths are correct
- Make sure you have necessary permissions

## Next Steps

Once comfortable with the MVP:
1. Add AST-aware editing (Phase 2)
2. Implement semantic search with embeddings
3. Add git integration
4. Build VS Code extension

## Getting Help

- Check tool execution panels for error details
- Flux shows what tools it's using and their results
- Use `exit` or `quit` to leave interactive mode

Happy coding! 🚀
