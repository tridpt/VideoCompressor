# Contributing to Super Video Compressor

Thanks for your interest in contributing! This guide covers how to set up the
project, run the tests, and submit changes.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/<your-username>/VideoCompressor.git
   cd VideoCompressor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest
   ```

3. Run the app:
   ```bash
   python main.py
   ```

## Running Tests

The test suite covers the pure-logic functions (no GUI required), so it runs fast:

```bash
python -m pytest test_logic.py -v
```

All tests must pass before a pull request can be merged. The same suite runs
automatically in CI on Python 3.10, 3.11, and 3.12.

## Coding Guidelines

- **Keep logic testable.** When adding new behavior, prefer writing it as a
  pure module-level function (like `make_output_path`, `format_eta`,
  `format_savings`) and have the GUI class delegate to it. Add matching tests
  in `test_logic.py`.
- **Don't block the UI.** Heavy work (FFmpeg) runs in a background thread; all
  UI updates from that thread must go through `self.after(0, ...)`.
- **Match the existing style.** The codebase uses clear Vietnamese comments and
  descriptive names. Follow the surrounding conventions.
- See [DOCS.md](DOCS.md) for architecture details and important technical notes
  (e.g. the stderr deadlock handling).

## Submitting Changes

1. Create a branch for your change:
   ```bash
   git checkout -b feature/my-change
   ```
2. Make your changes and ensure tests pass.
3. Write a clear, concise commit message describing what changed and why.
4. Push your branch and open a pull request against `main`.
5. Describe what you changed, how you tested it, and any limitations.

## Reporting Bugs

Open an issue and include:
- What you did (steps to reproduce)
- What you expected to happen
- What actually happened
- Your OS and Python version
- Relevant output from `video_compressor_error.log` if a compression failed
