"""Safe command execution tool for CrewAI."""

import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

DEFAULT_BLOCKED_PATTERNS = [
    "sudo ",
    "su ",
    "rm -rf",
    "rm -fr",
    "rm -r /",
    "rm -r ~",
    "rm -R",
    "dd if=",
    "mkfs",
    ":(){ :|:& };:",
    "chmod -R 777",
    "chown -R",
    "> /dev/sd",
    "> /dev/hd",
    "mv /* ",
    "wget ",
    "curl ",
    "nc -l",
    "ncat ",
    "shutdown",
    "reboot",
    "init 0",
    "init 6",
    "halt",
    "poweroff",
    "systemctl stop",
    "service stop",
    "kill -9 -1",
    "killall",
    "pkill -9",
    "iptables",
    "ufw disable",
    "crontab -r",
    "userdel",
    "usermod",
    "passwd",
    "visudo",
]

DEFAULT_ALLOWED_COMMANDS = [
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "pwd",
    "echo",
    "wc",
    "sort",
    "uniq",
    "cut",
    "awk",
    "sed",
    "tr",
    "diff",
    "touch",
    "mkdir",
    "cp",
    "mv",
    "rm",
    "date",
    "which",
    "env",
    "printenv",
    "type",
    "uname",
    "whoami",
    "id",
    "git",
    "python",
    "python3",
    "pip",
    "pip3",
    "npm",
    "node",
    "yarn",
    "cargo",
    "rustc",
    "go",
    "make",
    "cmake",
    "gcc",
    "g++",
    "clang",
    "pytest",
    "jest",
    "mypy",
    "ruff",
    "black",
    "isort",
    "prettier",
    "eslint",
    "tsc",
    "uv",
    "poetry",
    "hatch",
    "rg",
    "fd",
    "bat",
    "exa",
    "tree",
    "jq",
    "yq",
    "http",
    "curlie",
    "sleep",
    "true",
    "false",
    "test",
    "[",
    "xargs",
    "parallel",
]


class ExecSchema(BaseModel):
    """Schema for exec operation."""

    command: str = Field(
        ...,
        description="Shell command to execute.",
    )
    timeout: int = Field(
        default=60,
        description="Timeout in seconds. Max 300.",
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Working directory. Defaults to current directory.",
    )


class ExecTool(BaseTool):
    """Safe command execution tool for CrewAI agents.

    Implements security best practices:
    - Blocklist for dangerous patterns (sudo, rm -rf, etc.)
    - Allowlist for approved commands
    - Timeout enforcement
    - Output size limits
    - Working directory restriction
    """

    name: str = "Exec Tool"
    description: str = """
    Execute shell commands safely. Only approved commands are allowed.
    Dangerous operations (sudo, rm -rf, system modifications) are blocked.
    Returns command output with status code.
    """
    blocked_patterns: list[str] = Field(
        default_factory=lambda: DEFAULT_BLOCKED_PATTERNS.copy(),
        description="Patterns that block command execution.",
    )
    allowed_commands: list[str] = Field(
        default_factory=lambda: DEFAULT_ALLOWED_COMMANDS.copy(),
        description="Commands allowed to execute.",
    )
    max_timeout: int = Field(
        default=300,
        description="Maximum allowed timeout in seconds.",
    )
    max_output_size: int = Field(
        default=100000,
        description="Maximum output size in bytes.",
    )
    allowed_directories: list[str] = Field(
        default_factory=list,
        description="Allowed working directories. Empty = all allowed.",
    )
    require_allowlist: bool = Field(
        default=True,
        description="If True, only allowlisted commands execute.",
    )

    def _parse_command(self, command: str) -> tuple[str, list[str]]:
        """Parse command into binary and arguments."""
        try:
            parts = shlex.split(command)
            if not parts:
                return "", []
            return parts[0], parts
        except ValueError:
            return command.split()[
                0
            ] if command.split() else "", command.split()

    def _check_blocked_patterns(self, command: str) -> Optional[str]:
        """Check if command contains blocked patterns."""
        cmd_lower = command.lower()
        for pattern in self.blocked_patterns:
            if pattern.lower() in cmd_lower:
                return (
                    f"Blocked: command contains forbidden pattern '{pattern}'"
                )
        return None

    def _check_allowed_command(self, binary: str) -> Optional[str]:
        """Check if command binary is allowed."""
        if not self.require_allowlist:
            return None

        binary_name = Path(binary).name
        if binary_name not in self.allowed_commands:
            return f"Blocked: '{binary_name}' is not in allowed commands"
        return None

    def _validate_directory(self, cwd: Optional[str]) -> Optional[str]:
        """Validate working directory is allowed."""
        if not cwd or not self.allowed_directories:
            return None

        try:
            resolved = Path(cwd).resolve()
            for allowed in self.allowed_directories:
                if resolved.is_relative_to(Path(allowed).resolve()):
                    return None
            return f"Blocked: directory '{cwd}' is not in allowed directories"
        except Exception as e:
            return f"Invalid directory: {e}"

    def _validate_rm_command(self, args: list[str]) -> Optional[str]:
        """Additional validation for rm commands."""
        dangerous_flags = {"-rf", "-fr", "-r", "-R", "--no-preserve-root"}
        protected_paths = {"/", "~", "/home", "/etc", "/usr", "/var", "/root"}

        has_recursive = any(arg in dangerous_flags for arg in args)
        targets_root = any(
            arg in protected_paths
            or arg.startswith("/")
            and not arg.startswith("/tmp")
            for arg in args
            if not arg.startswith("-")
        )

        if has_recursive and targets_root:
            return "Blocked: recursive rm on protected path"

        return None

    def is_command_safe(
        self, command: str, cwd: Optional[str] = None
    ) -> tuple[bool, str]:
        """Check if command is safe to execute.

        Returns:
            (is_valid, error_message)
        """
        binary, args = self._parse_command(command)

        if not binary:
            return False, "Empty command"

        blocked = self._check_blocked_patterns(command)
        if blocked:
            return False, blocked

        not_allowed = self._check_allowed_command(binary)
        if not_allowed:
            return False, not_allowed

        dir_error = self._validate_directory(cwd)
        if dir_error:
            return False, dir_error

        binary_name = Path(binary).name
        if binary_name == "rm":
            rm_error = self._validate_rm_command(args)
            if rm_error:
                return False, rm_error

        return True, ""

    def execute(
        self,
        command: str,
        timeout: int = 60,
        cwd: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a shell command safely.

        Args:
            command: Shell command to execute.
            timeout: Timeout in seconds (max 300).
            cwd: Working directory.

        Returns:
            Dict with: success, exit_code, stdout, stderr, duration_ms
        """
        is_valid, error = self.is_command_safe(command, cwd)
        if not is_valid:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": error,
                "duration_ms": 0,
            }

        timeout = min(timeout, self.max_timeout)
        work_dir = Path(cwd).resolve() if cwd else Path.cwd()

        start = time.monotonic()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(work_dir),
            )

            stdout = result.stdout[: self.max_output_size]
            stderr = result.stderr[: self.max_output_size]

            if len(result.stdout) > self.max_output_size:
                stderr += (
                    f"\n[Output truncated - {len(result.stdout)} bytes total]"
                )
            if len(result.stderr) > self.max_output_size:
                stderr += (
                    f"\n[Stderr truncated - {len(result.stderr)} bytes total]"
                )

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": int((time.monotonic() - start) * 1000),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "duration_ms": timeout * 1000,
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution error: {e}",
                "duration_ms": int((time.monotonic() - start) * 1000),
            }

    def _run(self, command: str, **kwargs: Any) -> str:
        """Run the tool (called by CrewAI framework)."""
        result = self.execute(command, **kwargs)

        lines = [f"Exit code: {result['exit_code']}"]
        if result["stdout"]:
            lines.append(f"STDOUT:\n{result['stdout']}")
        if result["stderr"]:
            lines.append(f"STDERR:\n{result['stderr']}")
        lines.append(f"Duration: {result['duration_ms']}ms")

        return "\n".join(lines)

    def add_allowed_command(self, command: str) -> None:
        """Add command to allowlist."""
        if command not in self.allowed_commands:
            self.allowed_commands.append(command)

    def remove_allowed_command(self, command: str) -> None:
        """Remove command from allowlist."""
        if command in self.allowed_commands:
            self.allowed_commands.remove(command)

    def add_blocked_pattern(self, pattern: str) -> None:
        """Add pattern to blocklist."""
        if pattern not in self.blocked_patterns:
            self.blocked_patterns.append(pattern)
