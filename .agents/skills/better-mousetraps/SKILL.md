---
name: better-mousetraps
description: Evaluate build-vs-import decisions before writing new functionality. Use when (1) about to implement non-trivial functionality that likely exists as a library, (2) the user's request could be solved by an existing tool or package, (3) you catch yourself writing utility code (parsing, validation, HTTP, crypto, dates, etc.) that smells like a solved problem, or (4) planning a feature and need to weigh develop-in-house vs. adopt a dependency.
---

# Better Mousetraps: Build vs. Import

Before writing non-trivial functionality from scratch, **stop and research whether a well-maintained solution already exists**. This applies whether the impulse to build comes from you or from the user's request.

> "Most advice for technical leaders over-emphasizes the short-term risks of innovating too much, and under-emphasizes the long-term risks of innovating too little." — Marc Brooker

The inverse is equally true for implementation work: most developers (and coding agents) over-emphasize the appeal of a custom solution and under-emphasize the value of a battle-tested dependency.

## When This Skill Triggers

Activate this decision framework whenever you're about to:

- Write a utility function for a well-known problem domain (dates, parsing, validation, retries, HTTP, crypto, serialization, CLI argument parsing, etc.)
- Implement an algorithm or data structure that has known optimized implementations
- Build an integration layer with an external service or protocol
- Create infrastructure code (logging, config, caching, task queues, etc.)
- Solve a problem where you suspect libraries exist but aren't sure which

## Step 1: Research First

**Before writing any code**, spend time investigating existing options. This is not optional—it's the most valuable step.

### How to Research

1. **Web search** for `"python <problem domain> library"`, `"best <X> library 2025"`, `"<framework> <problem> package"`, etc.
2. **Check PyPI / npm / crates.io** (whatever applies) for packages in the domain
3. **Look at what the project already depends on**—many libraries have sub-features that solve adjacent problems (e.g., `pydantic` already handles validation, `httpx` already does retries with the right config)
4. **Check the project's existing codebase**—maybe this is already solved elsewhere in the repo
5. **Read "awesome" lists** and community recommendations for the domain

### What to Look For in a Dependency

| Signal | Good | Concerning |
|--------|------|------------|
| Maintenance | Regular commits, responsive issues | Abandoned, no releases in 2+ years |
| Adoption | Widely used, many dependents | Few downloads, no community |
| Scope | Focused, does one thing well | Kitchen-sink, pulls in heavy transitive deps |
| License | Compatible with project (MIT, Apache, BSD) | Copyleft or unclear licensing |
| Quality | Good docs, typed, tested | No docs, no types, no tests |
| Fit | API matches your use case naturally | Requires heavy wrapping or workarounds |

## Step 2: Evaluate the Tradeoffs

Use these questions (adapted from [Brooker's framework](https://brooker.co.za/blog/2024/03/04/mousetrap.html)) to make a deliberate decision:

### Questions That Favor Importing

- **Is this a solved problem?** If the problem is well-understood with known best practices, prefer a library that encodes that knowledge.
- **Is correctness critical?** Crypto, date math, Unicode handling, compression—these have subtle edge cases that mature libraries handle and hand-rolled code won't.
- **Will you actually maintain this?** Custom code requires ongoing ownership. A dependency externalizes that burden.
- **Are you solving the same problem as everyone else?** If your problem isn't unique, your solution shouldn't be either.

### Questions That Favor Building

- **Is your problem genuinely different?** Not "slightly different"—meaningfully different in ways that existing solutions can't accommodate.
- **Is the dependency heavier than the problem?** If you need one function from a 50MB package, maybe write the function.
- **Do you need deep control?** If you'll need to modify internals frequently, owning the code may be simpler.
- **Is the ecosystem immature or unstable?** If available libraries are abandoned, poorly maintained, or have breaking changes every release, building may be more stable.
- **Is this core differentiating logic?** If this is the thing that makes your project uniquely valuable, owning it makes sense.

### The Scale Question

Different scales require different solutions. A quick script might inline a 5-line parser; a production service should use a hardened library. Match the solution to the context.

## Step 3: Present the Options

When you've identified viable existing solutions, **present them to the user** before building from scratch. Structure your recommendation like this:

```
I found existing libraries that handle <problem>:

1. **<library-a>** — <one-line description>. <fit assessment>.
2. **<library-b>** — <one-line description>. <fit assessment>.
3. **Build from scratch** — <what that would involve and why it might be justified>.

I'd recommend <option> because <reasoning>. Want me to proceed with that?
```

Always include the "build from scratch" option with an honest assessment—sometimes it really is the right choice.

## Step 4: Integrate Thoughtfully

If adopting a dependency:

- **Wrap it at the boundary** if the API might change or you might swap implementations later
- **Pin versions** appropriately (exact for applications, compatible ranges for libraries)
- **Check for conflicts** with existing dependencies
- **Add it to the right dependency group** (dev, optional, core)
- **Don't over-abstract**—a thin wrapper is fine, a full adapter layer is usually unnecessary

If building from scratch:

- **Document why** you didn't use an existing solution (a brief comment is sufficient)
- **Keep the scope minimal**—solve your actual problem, not the general case
- **Consider extracting later** if the solution proves generally useful

## Anti-Patterns to Avoid

1. **"Not Invented Here" syndrome**: Rejecting libraries because custom code feels more satisfying or controllable, without evaluating the actual tradeoffs.

2. **Cargo-culting the user's request**: If the user says "write a function that does X", don't blindly comply if X is a well-solved problem. Suggest the library, explain why, and let them decide.

3. **Premature generalization**: Building a general-purpose solution when a library already provides one. Your custom version will be less tested, less documented, and less maintained.

4. **Dependency phobia**: Refusing all dependencies out of principle. Dependencies have costs, but so does hand-rolled code—and hand-rolled code has the additional cost of being untested by the broader community.

5. **Shallow research**: Checking one search result and concluding "nothing exists." Spend real time looking. Try different search terms. Check what similar projects use.

## Quick Reference: Common "Already Solved" Domains

These domains almost always have mature, well-tested libraries. Default to importing unless you have a specific reason not to:

| Domain | Think twice before hand-rolling |
|--------|-------------------------------|
| Date/time manipulation | Timezone bugs are legendary |
| HTTP clients/servers | Connection pooling, retries, timeouts |
| JSON/YAML/TOML parsing | Edge cases in specs are subtle |
| Argument/CLI parsing | Flag handling, help generation |
| Logging/structured logging | Output formatting, handlers, levels |
| Validation | Schema validation, error messages |
| Authentication/crypto | Security-critical, easy to get wrong |
| Database ORMs/queries | SQL injection, connection management |
| Retry/backoff logic | Jitter, exponential backoff, circuit breaking |
| Rate limiting | Token bucket, sliding window algorithms |
| Path/URL manipulation | Cross-platform edge cases |
| Test fixtures/factories | Object generation, fake data |
| CSV/Excel parsing | Encoding, malformed input handling |
| Email parsing/sending | MIME, encoding, deliverability |
| Markdown/HTML processing | XSS, spec compliance |
