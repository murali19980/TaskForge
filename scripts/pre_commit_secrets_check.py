import sys
import os
import re

def main():
    has_error = False
    # Regex to detect API key assignment with potential actual values (not variable references)
    key_pattern = re.compile(r"OPENROUTER_API_KEY[ \t]*=[ \t]*['\"]?[a-zA-Z0-9_\-]+['\"]?")

    for filepath in sys.argv[1:]:
        basename = os.path.basename(filepath)
        if basename == ".env":
            print(f"Error: Committing '.env' is blocked: {filepath}")
            has_error = True
            continue

        if os.path.isdir(filepath):
            continue

        # Exclude files where referencing the key name is expected
        if filepath.endswith("config.py") or filepath.endswith("main.py") or filepath.endswith("test_api.py") or filepath.endswith("llm_provider.py") or filepath.endswith("pre_commit_secrets_check.py") or filepath.endswith(".github/workflows/test.yml") or filepath.endswith(".env.example") or filepath.endswith("test_models.py"):
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "sk-or-v1-" in content:
                    print(f"Error: Detected potential OpenRouter API Key ('sk-or-v1-...') in file: {filepath}")
                    has_error = True

                if key_pattern.search(content):
                    print(f"Error: Detected potential API key assignment to OPENROUTER_API_KEY in file: {filepath}")
                    has_error = True
        except Exception:
            pass

    if has_error:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
