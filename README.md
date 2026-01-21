# AutoCommit

I got tired of writing commit messages. So I vibe coded this to let AI do it for me.

If you're also too lazy to type `git add`, `git commit -m "..."`, and `git push` every single time, this tool is for you.

## What it does

Runs one command. AI looks at your changes, writes a commit message, commits everything, and pushes it. Done.

## Installation

```bash
pip install autocommit
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
autocommit
```

That's it. Your changes are committed and pushed with an AI-generated message.

### Options

```bash
autocommit                    # Do everything automatically
autocommit -m "my message"    # Use your own message
autocommit --no-push          # Commit but don't push
autocommit --dry-run          # See what would happen
autocommit -v                 # Verbose output
```

## Why?

Because typing commit messages is easy but boring. This tool saves me from doing minimal work that I'm too lazy to do manually.

## License

MIT - Do whatever you want with it
