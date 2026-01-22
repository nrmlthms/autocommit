# LazyCommit

I got tired of writing commit messages. So I vibe coded this to let AI do it for me.

If you're also too lazy to type `git add`, `git commit -m "..."`, and `git push` every single time, this tool is for you.

## What it does

Runs one command. AI looks at your changes, writes a commit message, commits everything, and pushes it. Done.

## Installation

```bash
pip install lazycommit-cli
```

Or install from GitHub:

```bash
pip install git+https://github.com/nrmlthms/autocommit.git
```

## Setup

Get an OpenAI API key and set it:

```bash
export OPENAI_API_KEY="your-key-here"
```

## Usage

In any git repo, just run:

```bash
lazycommit
```

That's it. Your changes are committed and pushed with an AI-generated message.

### Options

```bash
lazycommit                    # Do everything automatically
lazycommit -m "my message"    # Use your own message
lazycommit --no-push          # Commit but don't push
lazycommit --dry-run          # See what would happen
lazycommit -v                 # Verbose output
lazycommit --safe-mode        # Create backup branch and enable rollback
lazycommit --model gpt-4      # Use a different OpenAI model
```

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
  "verbose_by_default": false
}
```

### Configuration options

- `model`: OpenAI model to use (default: "gpt-4o-mini")
- `base_url`: Custom API endpoint for OpenRouter or other providers (default: null, uses OpenAI)
- `temperature`: LLM temperature for message generation (default: 0.7)
- `max_tokens`: Maximum tokens for commit message (default: 100)
- `max_message_length`: Maximum commit message length in characters (default: 500)
- `max_context_files`: Maximum files to include in LLM context (default: 10)
- `max_diff_lines`: Maximum diff lines per file to include (default: 20)
- `push_by_default`: Whether to push by default (default: true)
- `safe_mode_by_default`: Enable safe mode by default (default: false)
- `verbose_by_default`: Enable verbose output by default (default: false)

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

## Why?

Because typing commit messages is easy but boring. This tool saves me from doing minimal work that I'm too lazy to do manually.

## License

MIT - Do whatever you want with it
