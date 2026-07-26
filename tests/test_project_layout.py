import os

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def test_dirs_exist_and_have_gitkeep():
    for rel_dir in ("input", "output", "logs", "var/tmp"):
        d = os.path.join(PROJECT_ROOT, rel_dir)
        assert os.path.isdir(d), f"{rel_dir} directory missing"
        gitkeep = os.path.join(d, ".gitkeep")
        assert os.path.isfile(gitkeep), f"{rel_dir}/.gitkeep missing"


def test_env_example_exists():
    env_path = os.path.join(PROJECT_ROOT, ".env.example")
    assert os.path.isfile(env_path), ".env.example missing"
    with open(env_path) as f:
        content = f.read()
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL", "INPUT_DIR", "OUTPUT_DIR", "LOGS_DIR", "TEMP_DIR"):
        assert key in content, f"{key} not found in .env.example"


def test_changelog_exists():
    assert os.path.isfile(os.path.join(PROJECT_ROOT, "CHANGELOG.md"))
