version: 2025.08.04-1-en

# Pull Request Guide & Checklist

Welcome, and thank you for choosing to contribute to the Open-LLM-VTuber project! We are deeply grateful for the effort of every contributor.

This guide is designed to help all contributors, maintainers, and even LLMs collaborate effectively, ensuring the project's high quality, maintainability, and long-term health. Please refer to this guide both when submitting a Pull Request (PR) and when reviewing PRs from others.

We believe that clear standards and processes are not only the cornerstone of project maintenance but also an excellent opportunity for us to learn and grow together.

⚠️ The coding standards mentioned below apply primarily to new code submissions. Some legacy code may not currently pass all type checks. We are working to fix this incrementally, but it will take time. When encountering type errors reported by the type checker, please focus only on the parts of the code your PR modifies. Adhere to principle **A1 (A PR should do one thing)**. If you wish to help fix existing type errors, please open a separate PR for that purpose.

---

### A. The Golden Rule: Atomic PRs

This is our most important principle. Please adhere to it strictly.

**A1. A single PR should do one thing, and one thing only.**

* **Good examples 👍:**
    * `fix: Resolve audio stuttering on macOS`
    * `feat: Add OpenAI TTS support`
    * `refactor: Rework the audio_processing module`
* **Bad examples 👎:**
    * `fix: Resolve bug A, bug B, and implement feature C`

**Why is this so important?**

* **Easy to Review:** Small, focused PRs allow reviewers to understand your changes more quickly and deeply, leading to higher-quality feedback. As stated in *The Pragmatic Programmer*, "Tip 38: It's Easier to Change Sooner." Small PRs facilitate rapid feedback loops.
* **Easy to Track:** When a problem arises in the future, a clean Git history (thanks to `git bisect`) allows us to quickly pinpoint the exact change that introduced the issue.
* **Easy to Revert:** If a small change introduces a bug, we can easily revert it without impacting other unrelated features or fixes.

### B. Contributor's Checklist: Submitting My PR

Before you submit your PR, please confirm each of the following items. This not only significantly speeds up the merge process but is also a sign of respect for your own work and for your fellow collaborators.

#### B1. PR Title & Description

* [ ] **B1.1: Clear Title:** The title should concisely summarize the core content of the PR. For example: `feat: Add OpenAI TTS support` or `fix: Resolve audio stuttering on macOS`. Remember, a PR should only do one thing (A1).
* [ ] **B1.2: Complete Description:** The description area should clearly explain:
    * **What:** Briefly describe the purpose and context of this PR.
    * **Why:** Explain the necessity of this change. If it's a bug fix, please link to the relevant Issue.
    * **How:** Briefly outline the technical implementation approach.
    * **How to Test:** Provide clear, step-by-step instructions so that reviewers can reproduce and verify your work.

#### B2. Code Quality Self-Check

* [ ] **B2.1: Atomicity:** Does my PR strictly adhere to the **A1** principle?
* [ ] **B2.2: Formatting & Linting:** Have I run and passed the following commands locally?
    ```bash
    uv run ruff format
    uv run ruff check
    ```
* [ ] **B2.3: Naming Conventions:** Do all variable, function, and module names follow **D3.2**? (i.e., PEP 8's `snake_case` style).
* [ ] **B2.4: Type Hints & Docstrings:**
    * [ ] **B2.4.1:** Do all new or modified functions include Type Hints compliant with **D3.3**?
    * [ ] **B2.4.2:** Do all new or modified functions include English Docstrings compliant with **D3.3**?
* [ ] **B2.5: Dependency Management:** If I've added a new third-party library, have I carefully considered and followed the principles in **D5. Dependency Management**?
* [ ] **B2.6: Cross-Platform Compatibility:** Does my code run correctly on macOS, Windows, and Linux? If I've introduced components specific to a platform or GPU, have I made them optional?
* [ ] **B2.7: Comment Language:** Are all in-code comments, Docstrings, and console outputs in English? (This excludes i18n localization implementations, but English must be the default).

#### B3. Functional & Logical Self-Check

* [ ] **B3.1: Functional Testing:** Have I thoroughly tested my changes locally to ensure they work as expected and do not introduce new bugs?
* [ ] **B3.2: Alignment with Project Goals:** Do my changes align with the **D1. Core Project Goals** and not conflict with the **D2. Future Project Goals**?

#### B4. Documentation Update

* [ ] **B4.1: Documentation Sync:** If my PR introduces a new feature, a new configuration option, or any change that users need to be aware of, have I updated the relevant documentation in the docs repository (https://github.com/Open-LLM-VTuber/open-llm-vtuber.github.io)? (No exceptions).
* [ ] **B4.2: Changelog Entry:** (Optional, but recommended) Add a brief entry for your change under the "Unreleased" section in `CHANGELOG.md`.

### C. Maintainer's Checklist: Reviewing a PR

For the long-term health of the project, please carefully check the following items during a code review. You can reference these item numbers directly (e.g., "Regarding C2.1, I believe the maintenance cost of this feature might outweigh its benefits...") to initiate a discussion.

* [ ] **C1. Understand the Change:** Have I fully read and understood all the code and the intent behind this PR?
* [ ] **C2. Strategic Alignment:**
    * [ ] **C2.1: Necessity vs. Maintenance Cost:** Is this feature truly necessary? Does the value it provides justify the future maintenance cost we will incur? As Fred Brooks wrote in *The Mythical Man-Month*, "the conceptual integrity of the product... is the most important consideration in system design."
    * [ ] **C2.2: Core Goal Alignment:** Does it fully align with the **D1. Core Project Goals**?
    * [ ] **C2.3: Future Goal Alignment:** Is it consistent with, or at least not in conflict with, the **D2. Future Project Goals** and the project roadmap?
* [ ] **C3. Implementation Quality:**
    * [ ] **C3.1: Design Elegance:** Is the implementation sufficiently "simple" and "elegant"? Is there any over-engineering or premature optimization? "Simplicity is the ultimate sophistication." - Leonardo da Vinci.
    * [ ] **C3.2: Maintainability:** Is the code modular, loosely coupled, easy to understand, and testable?
    * [ ] **C3.3: Technical Detail Check:** Have all items from the contributor's self-checklist (**B2, B3, B4**) been met? (e.g., Are Type Hints accurate? Are Docstrings clear? Do Ruff checks pass?).
* [ ] **C4. Documentation Completeness:** Has the relevant documentation been created or updated, and is its content clear and accurate?

### D. Project Reference Standards

This section details our core values and technical specifications, which serve as the basis for all the checklists above.

#### D1. Core Project Goals

* **D1.1. Offline Operation:** The project's core functionality must support fully offline operation. Any feature requiring an internet connection must be an optional module.
* **D1.2. Frontend-Backend Separation:** Strictly adhere to a separated frontend-backend architecture to facilitate independent development and maintenance.
* **D1.3. Cross-Platform:** Core backend components must run on macOS, Windows, and Linux via CPU. Any component dependent on a specific platform or GPU must be optional.
* **D1.4. Updatability:** Users should be able to upgrade smoothly via an update script. Any Breaking Changes must be accompanied by a major version bump (e.g., v1 -> v2) and a switch to a new release branch.
* **D1.5. Maintainability:** The code must be simple, modular, decoupled, testable, and follow best practices.

#### D2. Future Project Goals

We are moving in the following directions. All new contributions should strive to align with these goals (though it's not strictly mandatory, as these goals will likely be implemented together in a future v2 refactor).

* **D2.1. GUI for Settings:** Gradually replace traditional `yaml` configuration files with a GUI-based settings interface.
* **D2.2. Plugin Architecture:** Build a plugin-based ecosystem, using a Launcher service to manage and run modules like ASR/TTS/LLM via a GUI.
* **D2.3. Stable API:** Provide a stable and reliable backend API for plugins and the frontend to consume.
* **D2.4. Automated Testing:** Comprehensively adopt `pytest`-based automated testing. New code should be designed with testability in mind.

#### D3. Detailed Coding Standards

**D3.1. Linter & Formatter**
We use **Ruff** to unify code style and check for potential issues. All submitted code must pass both `ruff format` and `ruff check`.

**D3.2. Naming Conventions**
* Follow Python's **PEP 8** style guide.
* Use **snake_case** for naming variables, functions, and modules.
* Names should be clear, descriptive, and unambiguous. Avoid single-letter variable names (except for loop counters).

**D3.3. Type Hints & Docstrings**
* **Why are they important?** Type Hints and Docstrings are the "manual" for your code. They help:
    * Other developers to quickly understand your code.
    * IDEs and static analysis tools (like VSCode, Ruff) to perform smarter error checking and code completion.
    * You, months from now, to understand the code you wrote yourself.
* **Type Hint Requirements:**
    * All function/method parameters and return values **must** include Type Hints.
    * The project targets **Python 3.10+**. Please use modern syntax, such as `str | None` instead of `Optional[str]`, and `list[str]` instead of `List[str]` (as per [PEP 604](https://peps.python.org/pep-0604/) and [PEP 585](https://peps.python.org/pep-0585/)).
    * Type Hints must be accurate. It is recommended to set VSCode's Python type checker to `basic` or `strict` mode for validation.
* **Docstring Requirements:**
    * All new or significantly modified public functions, methods, and classes **must** include an English Docstring.
    * We recommend the **Google style Docstring format**. It should include at least:
        * **Summary:** A one-line summary of the function's purpose.
        * **Args:** A description of each parameter's type and meaning.
        * **Returns:** A description of the return value's type and meaning.
    * **Example:**
        ```python
        def add(a: int, b: int) -> int:
            """Calculates the sum of two integers.

            Args:
                a: The first integer.
                b: The second integer.

            Returns:
                The sum of a and b.
            """
            return a + b
        ```

#### D4. Architectural Principles

* **D4.1. ASR/LLM/TTS Module Design:** When a library supports multiple models with vastly different configurations, prioritize user experience and ease of understanding.
    * It is recommended to encapsulate each complex model into a separate, independent module (e.g., `asr-whisper-api`, `asr-funasr`) rather than treating the entire library as one monolithic module. This simplifies user configuration and clarifies responsibilities.

#### D5. Dependency Management Principles

* **D5.1. Every new dependency must be carefully considered.**
    * Can this functionality be achieved with the standard library or an existing dependency?
    * Is the dependency's license compatible with our project?
    * Is the dependency's community active? How is its maintenance status? Is it secure and trustworthy? Does it pose a risk of supply chain attacks?

---

Thank you for taking the time to read this guide. We look forward to your contribution!

Finally, regarding the PR review process, please be patient. Our project is understaffed, and the core maintainers are also quite busy, so reviews may take some time. If a week passes without any response, I apologize in advance—I may have simply forgotten. Please feel free to ping me (@t41372) or other relevant maintainers in the Pull Request to remind us.