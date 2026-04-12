# Textual Framework Research - 2025/2026

**Research Date:** 2026-02-05
**Target Version:** Textual >=0.89
**Purpose:** Evaluate Textual for HybridCoder coding assistant TUI

---

## Executive Summary

Textual has matured significantly and is well-suited for building a modern coding assistant TUI. Key highlights:

- **Version 1.0.0** released Feb 16, 2025 (latest stable)
- Built-in **Collapsible widget** for expandable sections
- **Inline mode** support for preserving terminal scrollback
- **Markdown widget** with streaming support (perfect for LLM output)
- **Command Palette** (Ctrl+P) with fuzzy search built-in
- Rich layout system (grid, docking, multi-pane)
- Active development by Textualize

---

## 1. Collapsible/Expandable Widgets

### Status: Built-in widget available

The [Collapsible widget](https://textual.textualize.io/widgets/collapsible/) is a first-class container with a title that can show/hide content.

**Key Features:**
- Click or press Enter to toggle collapsed/expanded state
- Customizable initial state: `collapsed=True/False`
- Customizable symbols: `collapsed_symbol` and `expanded_symbol`
- Event handlers: `on_collapsible_collapsed`, `on_collapsible_expanded`
- Can add content via constructor or context manager

**Usage Example:**
```python
from textual.widgets import Collapsible

# Add content via constructor
Collapsible(title="Section 1", *children, collapsed=False)

# Or via context manager
with Collapsible(title="Section 2", collapsed=True):
    yield Label("Hidden content")
```

**Verdict:** Perfect for collapsible file trees, context sections, and debug output panels.

---

## 2. Alternate Screen vs Inline Mode

### Status: Both modes supported

**Alternate Screen (Default):**
- Full-screen TUI that takes over the terminal
- No scrollback buffer interaction
- Standard for most TUI apps

**Inline Mode (Added Recently):**
- App renders directly under the prompt
- [Blog post: Behind the Curtain of Inline Terminal Applications](https://textual.textualize.io/blog/2024/04/20/behind-the-curtain-of-inline-terminal-applications/)
- Preserves terminal history
- Mouse origin at top-left of terminal
- Cursor management handled by Textual

**Key Differences:**
- Alternate screen: No scrollback, full screen control
- Inline mode: Integrates with terminal history, limited to app height

**Recent Update:**
- [Smoother scrolling](https://textual.textualize.io/blog/2025/02/16/smoother-scrolling-in-the-terminal-mdash-a-feature-decades-in-the-making/) feature added Feb 16, 2025

**Verdict:** Use alternate screen for main TUI. Inline mode could be used for simpler "preview" or "inline chat" subcommands.

---

## 3. Markdown Rendering

### Status: Excellent support, optimized for streaming

The [Markdown widget](https://textual.textualize.io/widgets/markdown/) is designed for displaying Markdown documents and works extremely well with LLM streaming output.

**Key Features:**
- Syntax highlighting for code blocks
- Table support
- Streaming rendering (update method replaces content incrementally)
- Built on Rich rendering engine
- Can be anchored to bottom of scrollable view (perfect for chat)

**Streaming Example:**
```python
markdown_widget.update(new_markdown_content)  # Replaces content
```

**Performance Tip:**
- Use memoization for parsed Markdown blocks to avoid re-parsing on each token update
- Reference: [Markdown Chatbot with Memoization](https://ai-sdk.dev/cookbook/next/markdown-chatbot-with-memoization)

**Verdict:** This is the killer feature for an AI assistant. Textual's Markdown widget is purpose-built for streaming LLM output.

---

## 4. Mouse Selection and Clipboard

### Status: Built-in support with caveats

**Built-in Method:**
- `App.copy_to_clipboard(text)` uses OSC 52 ANSI escape sequence
- Works on most modern terminals
- **Does NOT work on macOS Terminal** (notable limitation)

**TextArea Widget:**
- Select text with mouse or Shift+arrow keys
- Toast popup confirms copy
- Can subclass to add custom copy bindings

**Alternative: pyperclip**
- Better cross-platform support
- Copies to machine where app runs (not SSH host)
- Recommended for distributed apps

**References:**
- [Copying and pasting in Textual](https://darren.codes/posts/textual-copy-paste/)
- [Copy and paste discussion](https://github.com/Textualize/textual/discussions/2190)

**Verdict:** Use OSC 52 for simplicity. Consider pyperclip if targeting macOS Terminal users.

---

## 5. Multi-Pane Layouts

### Status: Robust layout system

Textual provides multiple layout primitives for complex UIs:

**Layout Types:**
1. **Grid Layout** - Arrange widgets in rows/columns, spanning support
2. **Docked Widgets** - Fixed position (top/bottom/left/right edges)
3. **Vertical/Horizontal** - Linear stacking
4. **Containers** - Composable layout building blocks

**Best Practice:**
- Work from outside-in: fixed elements (header, footer, sidebar) first
- Use docking for sticky panels (file tree, context panel)
- Use grid for main content area

**Example Use Cases:**
- Left sidebar: Docked file tree (collapsible)
- Right sidebar: Docked context panel
- Center: Grid layout for chat + code preview
- Bottom: Docked input area

**References:**
- [Layout Guide](https://textual.textualize.io/guide/layout/)
- [Design a Layout How-To](https://textual.textualize.io/how-to/design-a-layout/)

**Verdict:** Fully featured. Can replicate any IDE-style layout.

---

## 6. Performance and Startup Overhead

### Textual Startup Performance

**Current State:**
- Generally fast for typical apps
- Some overhead with thousands of widgets
- Active optimization work by Textualize team

**Reference:**
- [Overhead of Python Asyncio tasks](https://textual.textualize.io/blog/2023/03/08/overhead-of-python-asyncio-tasks/)

### Python Lazy Imports (2025 Development)

**PEP 810 Approved (Nov 3, 2025):**
- Lazy imports coming to Python (not yet in 3.15.0a2)
- Opt-in feature for backward compatibility
- Up to **70% faster startup** on real-world CLIs
- Up to **40% memory reduction**

**Impact on HybridCoder:**
- Will benefit all Python CLIs, including Textual apps
- Not yet available, but coming soon
- Should defer heavy imports (tree-sitter, LSP, vector DB) until needed

**References:**
- [PEP 810 – Explicit lazy imports](https://peps.python.org/pep-0810/)
- [Python will offer lazy imports](https://www.theregister.com/2025/11/04/python_to_embrace_lazy_imports/)

**Verdict:** Textual itself is fast. For HybridCoder, apply standard Python optimization (lazy imports, deferred loading).

---

## 7. Key Bindings and Help Display

### Status: First-class feature with automatic help

**Binding Definition:**
```python
class MyApp(App):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),           # key, action, description
        ("ctrl+p", "command_palette", None),  # Built-in command palette
        Binding("?", "help", "Show help", show=True),  # Full Binding object
    ]
```

**Footer Widget:**
- Automatically displays active bindings from `Screen.active_bindings`
- Can hide specific bindings with `show=False`
- Binding groups for organized display
- Optional tooltips

**Command Palette:**
- Built-in fuzzy search (Ctrl+P)
- Searches all registered commands
- Extensible with custom commands
- Added in version 0.37.0

**References:**
- [Input Guide](https://textual.textualize.io/guide/input/)
- [Binding API](https://textual.textualize.io/api/binding/)
- [Command Palette Guide](https://textual.textualize.io/guide/command_palette/)
- [Command Palette announcement](https://textual.textualize.io/blog/2023/09/15/textual-0370-adds-a-command-palette/)

**Verdict:** Excellent built-in support. Footer + Command Palette provide comprehensive discoverability.

---

## 8. DataTable Performance (Bonus Finding)

### Status: Built-in widget with performance caveats

**Built-in DataTable:**
- Can handle thousands to millions of rows (Line API)
- May lag with very large datasets (1M+ rows)
- Beautiful and full-featured

**textual-fastdatatable:**
- Performance-focused reimplementation
- [GitHub: tconbeer/textual-fastdatatable](https://github.com/tconbeer/textual-fastdatatable)
- Pluggable data storage backend
- ArrowBackend: Optimized for large, immutable datasets
- Can load 300k rows "essentially instantly" vs minutes for built-in

**Tradeoff:**
- Fast reads, slow mutations (row add/remove)

**Verdict:** Use built-in DataTable unless displaying very large (100k+) datasets. Consider textual-fastdatatable for LSP reference results or search results.

---

## 9. Version History

**Key Releases:**
- **0.37.0** (Sept 15, 2023) - Added Command Palette
- **0.89.0** (Dec 5, 2024) - Latest before 1.0
- **1.0.0** (Feb 16, 2025) - Current stable release

**References:**
- [GitHub Releases](https://github.com/Textualize/textual/releases)
- [PyPI textual](https://pypi.org/project/textual/)

---

## Recommendations for HybridCoder

### Core UI Components

1. **Main App Structure:**
   - Use alternate screen mode (standard TUI)
   - Docked header (status bar)
   - Docked footer (key bindings help)
   - Multi-pane layout (file tree, chat, context)

2. **Chat Interface:**
   - Markdown widget for LLM output (streaming support)
   - Anchor to bottom of scrollable view
   - Memoize parsed blocks for performance

3. **Collapsible Panels:**
   - File tree: Collapsible sections by directory
   - Context panel: Collapsible sections for each context source
   - Debug output: Collapsible per-operation

4. **Keyboard Navigation:**
   - Define BINDINGS for all actions
   - Enable command palette (Ctrl+P) for discoverability
   - Show help in footer

5. **Copy/Paste:**
   - Use `App.copy_to_clipboard()` (OSC 52)
   - Add explicit "Copy" button for generated code
   - Consider pyperclip if macOS Terminal is a target

### Performance Strategy

1. **Lazy Loading:**
   - Defer tree-sitter, LSP, vector DB imports until needed
   - Use Textual's worker threads for heavy operations
   - Consider lazy imports when PEP 810 lands

2. **Async Everything:**
   - LSP queries: async workers
   - Vector search: async workers
   - LLM streaming: async for loop

3. **Memory Management:**
   - Limit chat history in UI (paginate older messages)
   - Use DataTable for large result sets (or textual-fastdatatable)
   - Clear unused widgets when switching views

---

## Sources

### Core Documentation
- [Textual - Home](https://textual.textualize.io/)
- [Python Textual: Build Beautiful UIs in the Terminal – Real Python](https://realpython.com/python-textual/)
- [GitHub - Textualize/textual](https://github.com/Textualize/textual)

### Widgets
- [Textual - Collapsible](https://textual.textualize.io/widgets/collapsible/)
- [Textual - Markdown](https://textual.textualize.io/widgets/markdown/)
- [Textual - TextArea](https://textual.textualize.io/widgets/text_area/)
- [Textual - DataTable](https://textual.textualize.io/widgets/data_table/)

### Layout & Design
- [Textual - Layout](https://textual.textualize.io/guide/layout/)
- [Textual - Design a Layout](https://textual.textualize.io/how-to/design-a-layout/)
- [Textual - Screens](https://textual.textualize.io/guide/screens/)

### Input & Interaction
- [Textual - Input](https://textual.textualize.io/guide/input/)
- [Textual - Binding API](https://textual.textualize.io/api/binding/)
- [Textual - Command Palette](https://textual.textualize.io/guide/command_palette/)
- [Copying and pasting in Textual - Darren Burns](https://darren.codes/posts/textual-copy-paste/)

### Blog Posts
- [Behind the Curtain of Inline Terminal Applications](https://textual.textualize.io/blog/2024/04/20/behind-the-curtain-of-inline-terminal-applications/)
- [Smoother scrolling in the terminal](https://textual.textualize.io/blog/2025/02/16/smoother-scrolling-in-the-terminal-mdash-a-feature-decades-in-the-making/)
- [Textual 0.37.0 adds a command palette](https://textual.textualize.io/blog/2023/09/15/textual-0370-adds-a-command-palette/)
- [Overhead of Python Asyncio tasks](https://textual.textualize.io/blog/2023/03/08/overhead-of-python-asyncio-tasks/)

### Performance
- [PEP 810 – Explicit lazy imports](https://peps.python.org/pep-0810/)
- [Python will offer lazy imports](https://www.theregister.com/2025/11/04/python_to_embrace_lazy_imports/)
- [GitHub - textual-fastdatatable](https://github.com/tconbeer/textual-fastdatatable)

### Examples & Tutorials
- [Building Modern Terminal Apps in Python with Textual and Markdown Support](https://medium.com/towardsdev/building-modern-terminal-apps-in-python-with-textual-and-markdown-support-4bb3e25e49db)
- [Guide to Building Interactive Terminal Apps with Textual](https://arjancodes.com/blog/textual-python-library-for-creating-interactive-terminal-applications/)

---

## Conclusion

**Textual is an excellent choice for HybridCoder's TUI.**

Key strengths:
- Mature (v1.0.0 released Feb 2025)
- Rich widget library (Collapsible, Markdown, DataTable, etc.)
- Built for streaming LLM output (Markdown widget)
- Excellent keyboard navigation and discoverability (Command Palette)
- Flexible multi-pane layouts
- Active development by Textualize

No blockers identified. All required features are available or easily implementable.
