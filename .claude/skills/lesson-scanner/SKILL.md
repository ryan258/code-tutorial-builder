---
name: lesson-scanner
description: "Use when the user wants to scan a project folder to discover learning opportunities for building tutorials. Runs the scanner, presents ranked opportunities, facilitates interactive discussion, and generates a tutorial for the selected opportunity. Examples: 'scan this project for lessons', 'find teaching opportunities', 'what can I teach from this codebase?'"
user_invocable: true
---

# Interactive Lesson Scanner

Scan a project directory, discover learning opportunities, and guide a teacher through selecting and generating a tutorial — all in an interactive conversation.

## Workflow

### Phase 1: Scan the project

Run the scanner CLI to get structured results:

```bash
python3 -m code_tutorial_builder scan <directory> --json --max 10
```

If the user didn't specify a directory, use the current working directory.

Parse the JSON output. You now have a ranked list of learning opportunities with:
- `title`, `file_path`, `components`, `concepts`
- `difficulty` (beginner/intermediate/advanced)
- `score` (0-1), `rationale`
- `gitnexus_context` (if GitNexus index is available)

### Phase 2: Enrich with GitNexus (if available)

If `gitnexus_available` is `true` in the scan results, use GitNexus MCP tools to add deeper context to the top opportunities:

For each of the top 3-5 opportunities:

1. **Find execution flows** the file participates in:
   ```
   gitnexus_query({query: "<main component names from the opportunity>"})
   ```

2. **Get symbol context** for key components:
   ```
   gitnexus_context({name: "<component_name>"})
   ```
   This reveals callers, callees, and which processes the component participates in — information that helps the teacher understand how the code fits in the larger system.

3. **Check functional area** membership:
   ```
   READ gitnexus://repo/<repo-name>/clusters
   ```
   This shows which cluster/functional area each component belongs to.

Add this context to your presentation of each opportunity (e.g., "This function is part of the 'request handling' flow and is called by 3 other modules").

### Phase 3: Present opportunities interactively

Present the opportunities in a clear, teacher-friendly format. For each opportunity, show:

```
## Opportunity N: <title>
**File:** <relative_path>
**Difficulty:** <level> | **Components:** <count> | **Dependency depth:** <depth>
**Concepts covered:** <concept list>
**Why this is a good lesson:** <rationale>
**GitNexus context:** <execution flows, callers, cluster> (if available)
```

Then invite the teacher to discuss:

> "Which of these interests you? I can show you the actual code for any of them, explain how the pieces connect, or suggest how to scope the lesson. You can also ask me to combine elements from different opportunities."

### Phase 4: Interactive discussion

Engage in back-and-forth with the teacher. Be prepared to:

- **Show code**: Read the file and walk through the components
- **Explain dependencies**: Use the scanner's dependency data and GitNexus context to explain how components relate
- **Suggest scoping**: If a file has too many components, suggest which subset to focus on
- **Compare opportunities**: Help the teacher weigh trade-offs between different options
- **Combine opportunities**: If the teacher wants elements from multiple files, discuss how to structure that
- **Adjust difficulty**: Suggest which components to include/exclude to hit a target difficulty level
- **Preview the lesson arc**: Describe what the tutorial would look like — "First we'd introduce X, then build Y on top of it, and the exercise would ask students to modify Z"

### Phase 5: Generate the tutorial

Once the teacher selects an opportunity, generate the tutorial:

```bash
python3 -m code_tutorial_builder generate -i <file_path> -o <output_path> --title "<title>" -v
```

Options to offer:
- `--format lesson` (teacher plan, default) or `--format handout` (student-facing)
- `--steps N` to control lesson length
- `--title` for a custom title
- `--ai` to enhance with AI-generated descriptions (requires OPENROUTER_API_KEY)

After generation, read the output file and offer to:
- Review it together
- Adjust the title or format
- Regenerate with different settings
- Generate a companion handout if they started with a lesson plan

## Tips for the conversation

- **Be a collaborator, not a menu.** Don't just list options — offer your opinion on which opportunities would make the best lessons and why.
- **Think pedagogically.** Consider what order concepts should be introduced, what prior knowledge students need, and what makes a satisfying lesson arc.
- **Use concrete code.** When discussing an opportunity, show actual snippets from the file so the teacher can see what students will be working with.
- **Respect the teacher's expertise.** They know their students. If they say "too advanced" or "my students love recursion", adjust your recommendations accordingly.
