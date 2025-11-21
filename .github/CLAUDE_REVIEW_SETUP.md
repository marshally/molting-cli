# Claude Code Review Setup

This GitHub Action automatically reviews pull requests using Claude AI according to Clean Code principles by Robert C. Martin.

## Features

- Automatic PR review on open, update, or reopen
- Reviews based on Clean Code principles including:
  - Meaningful Names
  - Function Quality (size, single responsibility, arguments)
  - Comment Quality
  - Formatting and Organization
  - Error Handling
  - Object-Oriented Design
  - Class Design (SRP, cohesion, coupling)
  - Test Quality (when applicable)
- Posts structured feedback directly on the PR
- Categorizes issues by severity (Critical / Important / Minor)
- Provides specific improvement suggestions

## Setup Instructions

### 1. Get an Anthropic API Key

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (you won't be able to see it again)

### 2. Add API Key to GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: Paste your Anthropic API key
6. Click **Add secret**

### 3. Enable GitHub Actions

The workflow is already configured in `.github/workflows/claude-code-review.yml`. It will automatically run on:
- New pull requests
- Updates to existing pull requests (new commits)
- Reopened pull requests

### 4. Required Permissions

The workflow requires these permissions (already configured):
- `contents: read` - To read the repository code
- `pull-requests: write` - To post review comments

## How It Works

1. **Trigger**: Workflow activates when a PR is opened, synchronized, or reopened
2. **Fetch Diff**: Gets the complete diff of changes in the PR
3. **Size Check**: Verifies the diff isn't too large for Claude's context window
4. **Claude Review**: Sends the diff to Claude with detailed Clean Code principles
5. **Post Comment**: Posts a structured review comment on the PR

## Review Structure

Each review includes:

### Summary
Brief overview of changes and overall quality assessment

### Strengths
Positive aspects following Clean Code principles

### Issues Found
Categorized list of issues with:
- **Severity**: Critical / Important / Minor
- **Location**: File and line reference
- **Principle**: Which Clean Code principle was violated
- **Issue**: Specific problem description
- **Suggestion**: How to improve

### Recommendations
General advice for ongoing improvement

## Customization

### Adjusting the Model

To use a different Claude model, edit line 108 in `.github/workflows/claude-code-review.yml`:

```yaml
"model": "claude-sonnet-4-20250514",  # Change this line
```

Available models:
- `claude-sonnet-4-20250514` - Latest Sonnet (balanced speed/quality)
- `claude-opus-4-20250514` - Most capable (slower, more expensive)
- `claude-3-5-sonnet-20241022` - Previous Sonnet version

### Adjusting Max Tokens

To allow longer reviews, edit line 109:

```yaml
"max_tokens": 4096,  # Increase for longer reviews
```

### Modifying Review Criteria

Edit the prompt in lines 37-91 to:
- Add additional code quality principles
- Focus on specific aspects (security, performance, etc.)
- Adjust review tone and detail level
- Add language-specific guidelines

### Large Diff Handling

Currently, diffs larger than 100KB are flagged but still processed. To handle them differently:

1. Edit the size check in lines 27-32
2. Add logic to summarize large diffs
3. Or split reviews across multiple comments

## Costs

- Claude Sonnet 4: ~$3 per million input tokens, ~$15 per million output tokens
- Typical PR review (5KB diff): ~$0.02-0.05
- Large PR review (50KB diff): ~$0.15-0.30

Monitor your usage at [https://console.anthropic.com/](https://console.anthropic.com/)

## Troubleshooting

### Review not appearing

1. Check **Actions** tab for workflow run status
2. Verify `ANTHROPIC_API_KEY` secret is set correctly
3. Check workflow logs for error messages
4. Ensure repository has Actions enabled

### API Key errors

- Error: "401 Unauthorized" → Check API key is valid and correctly set
- Error: "429 Too Many Requests" → Rate limit reached, wait and retry
- Error: "400 Bad Request" → Check model name is correct

### Review quality issues

- Too brief? Increase `max_tokens`
- Too generic? Add more specific criteria to the prompt
- Missing context? Ensure full diff is being captured

## Best Practices

1. **Don't rely solely on automated reviews** - Human review is still essential
2. **Use as a learning tool** - Help team members understand Clean Code principles
3. **Iterate on the prompt** - Customize based on your team's needs
4. **Monitor costs** - Set up billing alerts in Anthropic console
5. **Review the reviews** - Occasionally check if Claude's feedback is accurate

## Examples

### Good Review Example
```markdown
### Issues Found

**Important** | `molting/refactorings/extract_method.py:45`
- **Principle**: Functions - Arguments
- **Issue**: Function `extract_code_block` has 5 parameters, making it hard to understand and test
- **Suggestion**: Consider introducing a parameter object (e.g., `ExtractionConfig`) to group related parameters
```

### When Reviews Are Most Helpful

- Large refactoring PRs
- Code from junior developers learning Clean Code
- Legacy code improvements
- Architecture changes
- Public API design

## Additional Resources

- [Clean Code by Robert C. Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## License

This workflow configuration is part of the molting-cli project and follows the same MIT license.
