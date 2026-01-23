<div align="center">
  <img src="assets/lazy_commit.png" alt="LazyCommit Logo" width="200">

  # LazyCommit
</div>

I got tired of writing commit messages. So I vibe coded this to let AI do it for me.

If you're also too lazy to type `git add`, `git commit -m "..."`, and `git push` every single time, this tool is for you.

## What it does

Runs one command. AI looks at your changes, writes a commit message, commits everything, and pushes it. Done.

**New features:**
- 🎨 **Beautiful terminal output** with rich formatting, tables, and progress indicators
- 🤔 **Interactive mode** - review and edit AI-generated messages before committing
- 📊 **Repository stats** - view commit history and repository information
- ⏪ **Easy undo** - safely undo the last commit
- 🛡️ **Smart git state detection** - handles merge conflicts, detached HEAD, and other edge cases
- ⚙️ **Config management** - easily view and edit configuration

## Installation

```bash
pip install lazycommit-cli
```

Or install from GitHub:

```bash
pip install git+https://github.com/nrmlthms/lazycommit.git
```

## Setup

Get an OpenAI API key and set it:

```bash
export OPENAI_API_KEY="your-key-here"
```

## Usage

LazyCommit now uses subcommands for better organization and functionality.

### Commit Changes (Main Command)

```bash
lazycommit commit                    # Auto-detect, commit, and push
lazycommit commit --no-push          # Commit without pushing
lazycommit commit -m "my message"    # Use your own message
lazycommit commit --dry-run          # See what would happen
lazycommit commit -v                 # Verbose output
lazycommit commit --safe-mode        # Create backup branch
```

**Interactive Mode**: By default, LazyCommit will show you the AI-generated message and ask for confirmation:
- Press `y` to accept
- Press `n` to reject
- Press `e` to edit in your default editor

To skip the interactive prompt, provide a message with `-m` or set `interactive_mode: false` in config.

### Manage Configuration

```bash
lazycommit config --show              # Show current config
lazycommit config --edit              # Edit config file
lazycommit config --get model         # Get specific value
lazycommit config --set model --value gpt-4  # Set value
lazycommit config --reset             # Reset to defaults
```

### View Repository Stats

```bash
lazycommit stats              # Show stats for last 10 commits
lazycommit stats -n 20        # Show stats for last 20 commits
```

Displays a beautiful table with:
- Commit hash
- Author
- Date
- Message
- Repository summary (branch, total commits)

### Undo Last Commit

```bash
lazycommit undo              # Undo last commit (keep changes staged)
lazycommit undo --hard       # Undo and discard all changes
lazycommit undo -f           # Skip confirmation prompt
```

**Safe by default**: Uses soft reset to keep your changes staged. Use `--hard` only if you're sure you want to discard changes.

## Configuration

LazyCommit supports configuration via a `.lazycommitrc` file in your home directory.

### Creating a config file

Create `~/.lazycommitrc` with your preferences:

```json
{
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "max_tokens": 100,
  "max_message_length": 500,
  "max_context_files": 10,
  "max_diff_lines": 20,
  "push_by_default": true,
  "safe_mode_by_default": false,
  "verbose_by_default": false,
  "interactive_mode": true,
  "show_progress": true,
  "cache_enabled": true,
  "offline_mode": false
}
```

### Configuration options

**LLM Settings:**
- `model`: OpenAI model to use (default: "gpt-4o-mini")
- `base_url`: Custom API endpoint for OpenRouter or other providers (default: null)
- `temperature`: LLM temperature for message generation (default: 0.7)
- `max_tokens`: Maximum tokens for commit message (default: 100)

**Commit Message Settings:**
- `max_message_length`: Maximum commit message length in characters (default: 500)
- `max_context_files`: Maximum files to include in LLM context (default: 10)
- `max_diff_lines`: Maximum diff lines per file to include (default: 20)
- `max_input_tokens`: Maximum estimated input tokens before warning (default: 8000)

**Behavior Settings:**
- `push_by_default`: Whether to push by default (default: true)
- `safe_mode_by_default`: Enable safe mode by default (default: false)
- `verbose_by_default`: Enable verbose output by default (default: false)
- `interactive_mode`: Prompt to review/edit generated messages (default: true)
- `show_progress`: Show spinner/progress indicators during operations (default: true)

**Retry Settings:**
- `api_retry_enabled`: Enable automatic retry on API errors (default: true)
- `api_max_retries`: Maximum number of retry attempts (default: 3)
- `api_initial_retry_delay`: Initial delay between retries in seconds (default: 1.0)

**Cache Settings:**
- `cache_enabled`: Enable commit message caching (default: true)
- `cache_max_age_days`: Maximum age of cached messages in days (default: 30)
- `cache_max_entries`: Maximum number of cached messages (default: 100)

**Offline Mode:**
- `offline_mode`: If true, only use cache, never call API (default: false)

### Configuration priority

Settings are applied in this order (highest priority first):

1. Command-line arguments (e.g., `--model gpt-4`)
2. Environment variables (e.g., `OPENAI_API_KEY`, `LAZYCOMMIT_MODEL`)
3. Config file (`~/.lazycommitrc`)
4. Default values

### Environment variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `BASE_URL`: Custom API endpoint (e.g., for OpenRouter)
- `LAZYCOMMIT_MODEL`: Override the model setting
- `LAZYCOMMIT_TEMPERATURE`: Override temperature
- `LAZYCOMMIT_MAX_TOKENS`: Override max tokens
- `LAZYCOMMIT_PUSH_BY_DEFAULT`: Set to "true" or "false"
- `LAZYCOMMIT_SAFE_MODE`: Set to "true" or "false"
- `LAZYCOMMIT_VERBOSE`: Set to "true" or "false"

## Using OpenRouter

To use OpenRouter or other OpenAI-compatible APIs, set the `BASE_URL` environment variable or add `base_url` to your config file:

### Via environment variables:

```bash
export OPENAI_API_KEY="your-openrouter-api-key"
export BASE_URL="https://openrouter.ai/api/v1"
export LAZYCOMMIT_MODEL="anthropic/claude-3.5-sonnet"
```

### Via config file (`~/.lazycommitrc`):

```json
{
  "model": "anthropic/claude-3.5-sonnet",
  "base_url": "https://openrouter.ai/api/v1",
  "temperature": 0.7,
  "max_tokens": 100
}
```

Then set your OpenRouter API key:

```bash
export OPENAI_API_KEY="your-openrouter-api-key"
```

## Features

### 🎨 Beautiful Terminal Output

LazyCommit uses [rich](https://github.com/Textualize/rich) for beautiful terminal formatting:
- Colored output
- Progress spinners during slow operations
- Formatted tables for stats and config
- Syntax highlighting

### 🤔 Interactive Message Review

Review AI-generated commit messages before committing:
- See the generated message in a nice panel
- Accept, reject, or edit the message
- Opens your preferred editor (VISUAL/EDITOR env vars)
- Can be disabled with `interactive_mode: false` in config

### 🛡️ Smart Git State Detection

LazyCommit detects and handles various git repository states:
- **Merge conflicts**: Blocks commit and shows conflicted files
- **Detached HEAD**: Warns but allows commit with suggestion to create branch
- **Rebase in progress**: Blocks commit until rebase is complete
- **Cherry-pick/revert in progress**: Blocks commit with helpful suggestions
- **Normal state**: Commits proceed as expected

### 📊 Repository Statistics

View your commit history in a beautifully formatted table:
```bash
lazycommit stats
```

Shows:
- Recent commits (hash, author, date, message)
- Current branch
- Total commit count
- Repository path

### ⏪ Easy Undo

Made a mistake? Undo is simple:
```bash
lazycommit undo        # Soft reset (keeps changes)
lazycommit undo --hard # Hard reset (discards changes)
```

With confirmation prompts and clear warnings for safety.

### 💾 Smart Caching

LazyCommit caches commit messages to:
- Reduce API calls for identical changesets
- Speed up repeated operations
- Save on API costs

Cache automatically expires after 30 days and is limited to 100 entries.

### 🔄 Automatic Retry

API calls automatically retry on transient errors:
- Timeout errors
- Connection errors
- Rate limit errors
- 5xx server errors

With exponential backoff and configurable retry limits.

### 🔒 Safe Mode

Use `--safe-mode` to:
- Create a backup branch before committing
- Automatically rollback on push failures
- Keep your work safe during risky operations

## Why?

Because typing commit messages is easy but boring. This tool saves me from doing minimal work that I'm too lazy to do manually.

## Development

```bash
# Clone the repo
git clone https://github.com/nrmlthms/lazycommit.git
cd lazycommit

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy lazycommit
```

## License

MIT - Do whatever you want with it
