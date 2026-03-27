#!/usr/bin/env python3
"""ToraFirma documentation site builder.

Usage:
    tf_docs build
    tf_docs build --serve
    tf_docs serve
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


EXCLUDED_DIRS = {
    ".git",
    ".cursor",
    ".idea",
    ".vscode",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "outputs",
}

CODE_MARKER_FILES = (
    "pyproject.toml",
    "package.json",
    "setup.py",
    "setup.cfg",
)


@dataclass
class ProjectAudit:
    name: str
    root: Path
    has_docs: bool
    has_architecture_doc: bool
    docs_dir: Path | None


@dataclass
class MermaidResult:
    source: Path
    output: Path
    rendered: bool
    note: str


def _is_ignored_path(path: Path, root: Path) -> bool:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        relative_parts = path.parts
    return any(part in EXCLUDED_DIRS for part in relative_parts)


def _is_project_directory(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    if directory.name.startswith(".") or directory.name in EXCLUDED_DIRS:
        return False

    if any((directory / marker).exists() for marker in CODE_MARKER_FILES):
        return True

    if (directory / "__init__.py").exists():
        return True

    return any(directory.glob("*.py"))


def discover_projects(repo_root: Path) -> list[Path]:
    projects: list[Path] = []
    for child in sorted(repo_root.iterdir()):
        if _is_project_directory(child):
            projects.append(child)
    return projects


def audit_projects(repo_root: Path) -> list[ProjectAudit]:
    audits: list[ProjectAudit] = []
    for project_root in discover_projects(repo_root):
        docs_dir = project_root / "docs"
        architecture_doc = docs_dir / "architecture.md"
        audits.append(
            ProjectAudit(
                name=project_root.name,
                root=project_root,
                has_docs=docs_dir.exists(),
                has_architecture_doc=architecture_doc.exists(),
                docs_dir=docs_dir if docs_dir.exists() else None,
            )
        )
    return audits


def discover_docs_dirs(repo_root: Path, audits: list[ProjectAudit]) -> list[Path]:
    docs_dirs: list[Path] = []

    root_docs = repo_root / "docs"
    if root_docs.exists():
        docs_dirs.append(root_docs)

    for audit in audits:
        if audit.docs_dir and audit.docs_dir != root_docs:
            docs_dirs.append(audit.docs_dir)

    return sorted(set(docs_dirs))


def collect_docs_assets(docs_dir: Path, repo_root: Path) -> tuple[list[Path], list[Path]]:
    markdown_files: list[Path] = []
    mermaid_files: list[Path] = []

    for path in sorted(docs_dir.rglob("*")):
        if path.is_dir():
            continue
        if _is_ignored_path(path, repo_root):
            continue
        if path.suffix.lower() == ".md":
            markdown_files.append(path)
        elif path.suffix.lower() == ".mmd":
            mermaid_files.append(path)

    return markdown_files, mermaid_files


def copy_markdown_files(
    markdown_files: list[Path], repo_root: Path, output_root: Path
) -> dict[Path, Path]:
    copied: dict[Path, Path] = {}
    content_root = output_root / "content"

    for source in markdown_files:
        rel = source.relative_to(repo_root)
        target = content_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        copied[source] = target

    return copied


def resolve_mermaid_command() -> tuple[str, list[str]] | None:
    mmdc_bin = shutil.which("mmdc")
    if mmdc_bin:
        return "mmdc", [mmdc_bin]

    npx_bin = shutil.which("npx")
    if npx_bin:
        return "npx", [npx_bin, "--yes", "@mermaid-js/mermaid-cli"]

    return None


def render_mermaid_files(
    mermaid_files: list[Path], repo_root: Path, output_root: Path
) -> list[MermaidResult]:
    results: list[MermaidResult] = []
    command = resolve_mermaid_command()
    assets_root = output_root / "assets"

    if not mermaid_files:
        return results

    if command is None:
        for source in mermaid_files:
            rel = source.relative_to(repo_root).with_suffix(".svg")
            out = assets_root / rel
            results.append(
                MermaidResult(
                    source=source,
                    output=out,
                    rendered=False,
                    note="mmdc not available (install @mermaid-js/mermaid-cli)",
                )
            )
        return results

    _name, base_cmd = command
    for source in mermaid_files:
        rel = source.relative_to(repo_root).with_suffix(".svg")
        output_svg = assets_root / rel
        output_svg.parent.mkdir(parents=True, exist_ok=True)

        cmd = base_cmd + ["-i", str(source), "-o", str(output_svg)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if proc.returncode == 0:
            results.append(
                MermaidResult(
                    source=source, output=output_svg, rendered=True, note="rendered"
                )
            )
        else:
            note = proc.stderr.strip() or proc.stdout.strip() or "render failed"
            results.append(
                MermaidResult(
                    source=source,
                    output=output_svg,
                    rendered=False,
                    note=note,
                )
            )

    return results


def _link_from_index(index_path: Path, destination: Path) -> str:
    return os.path.relpath(destination, start=index_path.parent).replace("\\", "/")


def build_index(
    repo_root: Path,
    output_root: Path,
    audits: list[ProjectAudit],
    markdown_copies: dict[Path, Path],
    mermaid_results: list[MermaidResult],
) -> Path:
    index_path = output_root / "index.md"
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    total_projects = len(audits)
    projects_with_docs = sum(1 for audit in audits if audit.has_docs)
    missing_docs = [audit for audit in audits if not audit.has_docs]
    missing_arch = [audit for audit in audits if audit.has_docs and not audit.has_architecture_doc]
    rendered_diagrams = sum(1 for item in mermaid_results if item.rendered)
    failed_diagrams = [item for item in mermaid_results if not item.rendered]

    lines: list[str] = [
        "# ToraFirma Documentation Index",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Repository root: `{repo_root}`",
        "",
        "## Documentation Architecture",
        "",
        "This site is generated by `tf_docs build` and includes:",
        "",
        "- API references and technical docs from each project's `docs/` directory",
        "- Architecture diagrams from Mermaid `.mmd` sources rendered to `.svg`",
        "- User guides and standards from markdown source files",
        "- Project-level compliance audit for required architecture docs",
        "",
        "Required standard:",
        "",
        "- Every project should include `/docs/architecture.md`",
        "",
        "## Project Audit",
        "",
        f"- Projects detected: `{total_projects}`",
        f"- Projects with docs: `{projects_with_docs}`",
        f"- Missing docs directories: `{len(missing_docs)}`",
        f"- Missing `docs/architecture.md`: `{len(missing_arch)}`",
        "",
        "| Project | docs/ | docs/architecture.md |",
        "| --- | --- | --- |",
    ]

    for audit in audits:
        lines.append(
            f"| `{audit.name}` | {'yes' if audit.has_docs else 'no'} | "
            f"{'yes' if audit.has_architecture_doc else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Mermaid Rendering",
            "",
            f"- Diagrams rendered: `{rendered_diagrams}`",
            f"- Diagrams with errors or skipped: `{len(failed_diagrams)}`",
            "",
        ]
    )

    if failed_diagrams:
        lines.append("### Mermaid Issues")
        lines.append("")
        for item in failed_diagrams:
            rel_src = item.source.relative_to(repo_root).as_posix()
            lines.append(f"- `{rel_src}`: {item.note}")
        lines.append("")

    lines.extend(["## Documentation Files", ""])
    if not markdown_copies:
        lines.append("_No markdown files found in project docs directories._")
        lines.append("")
    else:
        for source, copy_target in sorted(markdown_copies.items(), key=lambda entry: str(entry[0])):
            rel_src = source.relative_to(repo_root).as_posix()
            link = _link_from_index(index_path, copy_target)
            lines.append(f"- [`{rel_src}`]({link})")
        lines.append("")

    lines.extend(["## Rendered Diagrams", ""])
    if not mermaid_results:
        lines.append("_No Mermaid `.mmd` files discovered._")
        lines.append("")
    else:
        for result in mermaid_results:
            rel_src = result.source.relative_to(repo_root).as_posix()
            if result.rendered:
                link = _link_from_index(index_path, result.output)
                lines.append(f"- [`{rel_src}`]({link})")
            else:
                lines.append(f"- `{rel_src}` (not rendered)")
        lines.append("")

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


def build_docs(repo_root: Path, output_root: Path) -> int:
    audits = audit_projects(repo_root)
    docs_dirs = discover_docs_dirs(repo_root, audits)

    markdown_files: list[Path] = []
    mermaid_files: list[Path] = []
    for docs_dir in docs_dirs:
        md_files, mmd_files = collect_docs_assets(docs_dir, repo_root)
        markdown_files.extend(md_files)
        mermaid_files.extend(mmd_files)

    output_root.mkdir(parents=True, exist_ok=True)
    markdown_copies = copy_markdown_files(markdown_files, repo_root, output_root)
    mermaid_results = render_mermaid_files(mermaid_files, repo_root, output_root)
    index_path = build_index(
        repo_root=repo_root,
        output_root=output_root,
        audits=audits,
        markdown_copies=markdown_copies,
        mermaid_results=mermaid_results,
    )

    print(f"Built documentation index: {index_path}")
    print(f"Markdown files copied: {len(markdown_copies)}")
    print(f"Mermaid files discovered: {len(mermaid_results)}")
    print(f"Mermaid files rendered: {sum(1 for item in mermaid_results if item.rendered)}")
    return 0


def serve_output(output_root: Path, port: int) -> int:
    if not output_root.exists():
        print(f"Error: output directory not found: {output_root}")
        return 1

    original_cwd = Path.cwd()
    os.chdir(output_root)
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving docs at http://localhost:{port}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping docs server.")
        finally:
            os.chdir(original_cwd)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tf_docs",
        description="Build and serve repository documentation from docs/ sources.",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_build = subparsers.add_parser(
        "build",
        help="Generate a unified documentation output from all project docs",
    )
    p_build.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to scan (default: current directory)",
    )
    p_build.add_argument(
        "--output",
        default="outputs/tf_docs/site",
        help="Output directory for generated docs",
    )
    p_build.add_argument(
        "--serve",
        action="store_true",
        help="Serve docs after a successful build",
    )
    p_build.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port used when --serve is enabled (default: 8000)",
    )

    p_serve = subparsers.add_parser(
        "serve",
        help="Serve an existing generated docs output",
    )
    p_serve.add_argument(
        "--output",
        default="outputs/tf_docs/site",
        help="Output directory to serve",
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for local HTTP server (default: 8000)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.command:
        print("No command specified. Use `tf_docs build` or `tf_docs serve`.")
        return 1

    if args.command == "build":
        repo_root = Path(args.repo_root).resolve()
        output_root = Path(args.output).resolve()
        result = build_docs(repo_root=repo_root, output_root=output_root)
        if result != 0:
            return result
        if args.serve:
            return serve_output(output_root=output_root, port=args.port)
        return 0

    if args.command == "serve":
        output_root = Path(args.output).resolve()
        return serve_output(output_root=output_root, port=args.port)

    print(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
