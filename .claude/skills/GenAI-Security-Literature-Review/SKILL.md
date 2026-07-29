```markdown
# GenAI-Security-Literature-Review Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the GenAI-Security-Literature-Review repository. The codebase is written in Python and focuses on literature review processes for GenAI security topics. It emphasizes clean code organization, consistent commit messaging, and a structured approach to file naming, imports, and exports. While no specific frameworks are detected, the repository follows clear conventions that support maintainability and collaboration.

## Coding Conventions

### File Naming
- Use **camelCase** for file names.
  - Example: `literatureParser.py`, `dataLoader.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parseDocument
    ```

### Export Style
- Use **named exports** (explicitly define what is exported).
  - Example:
    ```python
    def analyzePaper(paper):
        # analysis logic
        return result

    __all__ = ['analyzePaper']
    ```

### Commit Messages
- Use **conventional commit** patterns.
- Prefix commit messages with a type, such as `docs`.
- Example:
  ```
  docs: update literature sources in README
  ```

## Workflows

### Documentation Update
**Trigger:** When updating documentation or literature sources.
**Command:** `/update-docs`

1. Edit the relevant documentation files (e.g., `README.md`).
2. Use a conventional commit message prefixed with `docs`.
   - Example: `docs: add new GenAI security paper references`
3. Push your changes to the repository.

### Adding a New Module
**Trigger:** When adding new functionality or analysis logic.
**Command:** `/add-module`

1. Create a new Python file using camelCase naming.
   - Example: `riskAssessment.py`
2. Use relative imports to access shared utilities.
   - Example:
     ```python
     from .utils import loadData
     ```
3. Define functions and explicitly export them using `__all__`.
4. Write or update corresponding test files (see Testing Patterns).
5. Commit with a descriptive message.
   - Example: `docs: add risk assessment module`

## Testing Patterns

- Test files follow the pattern: `*.test.*` (e.g., `parser.test.py`).
- The specific testing framework is not specified; use standard Python testing practices.
- Example test structure:
  ```python
  def test_analyzePaper():
      sample_paper = {...}
      result = analyzePaper(sample_paper)
      assert result['score'] > 0
  ```

## Commands
| Command         | Purpose                                      |
|-----------------|----------------------------------------------|
| /update-docs    | Update documentation and commit changes      |
| /add-module     | Add a new module following conventions       |
```
