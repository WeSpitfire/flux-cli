"""File transaction manager for atomic multi-file operations with rollback."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import shutil
import tempfile


@dataclass
class Operation:
    """Represents a single file operation in a transaction."""
    op_type: str  # "move", "delete", "write", "edit"
    file_path: Path
    backup_path: Optional[Path] = None
    new_content: Optional[str] = None
    old_content: Optional[str] = None
    destination: Optional[Path] = None
    executed: bool = False


class FileTransaction:
    """
    Transaction manager for atomic file operations with rollback support.

    Usage:
        with FileTransaction(cwd) as txn:
            txn.move("a.py", "b.py")
            txn.edit("c.py", old_text, new_text)
            txn.delete("d.py")
            # Auto-commits on success, rolls back on exception
    """

    def __init__(self, cwd: Path):
        """Initialize transaction manager."""
        self.cwd = cwd
        self.operations: List[Operation] = []
        self.backup_dir: Optional[Path] = None
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        """Start transaction."""
        # Create temporary backup directory
        self.backup_dir = Path(tempfile.mkdtemp(prefix="flux_txn_"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End transaction - commit or rollback."""
        if exc_type is not None:
            # Exception occurred - rollback
            self.rollback()
            # Clean up backup directory
            if self.backup_dir and self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            return False  # Re-raise exception
        else:
            # No exception - commit
            if not self.committed:
                self.commit()
            # Clean up backup directory
            if self.backup_dir and self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            return True

    def add_operation(
        self,
        op_type: str,
        file_path: Path,
        **kwargs
    ) -> Operation:
        """Add an operation to the transaction."""
        op = Operation(
            op_type=op_type,
            file_path=file_path,
            **kwargs
        )
        self.operations.append(op)
        return op

    def move(self, source: str, destination: str) -> Dict[str, Any]:
        """Add a file move operation."""
        src_path = self._resolve_path(source)
        dst_path = self._resolve_path(destination)

        # Validate
        if not src_path.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        if dst_path.exists():
            raise FileExistsError(f"Destination already exists: {destination}")

        # Create backup
        backup_path = self._create_backup(src_path)

        # Add operation
        op = self.add_operation(
            "move",
            src_path,
            destination=dst_path,
            backup_path=backup_path
        )

        # Execute move
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        op.executed = True

        return {
            "operation": "move",
            "source": str(src_path),
            "destination": str(dst_path),
            "backed_up": True
        }

    def delete(self, path: str) -> Dict[str, Any]:
        """Add a file delete operation."""
        file_path = self._resolve_path(path)

        # Validate
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Create backup
        backup_path = self._create_backup(file_path)

        # Add operation
        op = self.add_operation(
            "delete",
            file_path,
            backup_path=backup_path
        )

        # Execute delete
        file_path.unlink()
        op.executed = True

        return {
            "operation": "delete",
            "path": str(file_path),
            "backed_up": True
        }

    def write(self, path: str, content: str) -> Dict[str, Any]:
        """Add a file write operation."""
        file_path = self._resolve_path(path)

        # Backup if file exists
        backup_path = None
        old_content = None
        if file_path.exists():
            backup_path = self._create_backup(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                old_content = f.read()

        # Add operation
        op = self.add_operation(
            "write",
            file_path,
            backup_path=backup_path,
            old_content=old_content,
            new_content=content
        )

        # Execute write
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        op.executed = True

        return {
            "operation": "write",
            "path": str(file_path),
            "bytes": len(content.encode('utf-8')),
            "backed_up": backup_path is not None
        }

    def edit(self, path: str, search: str, replace: str) -> Dict[str, Any]:
        """Add a file edit operation."""
        file_path = self._resolve_path(path)

        # Validate
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Read content
        with open(file_path, 'r', encoding='utf-8') as f:
            old_content = f.read()

        # Check search exists
        if search not in old_content:
            raise ValueError(f"Search text not found in {path}")

        # Create backup
        backup_path = self._create_backup(file_path)

        # Perform replacement
        new_content = old_content.replace(search, replace, 1)

        # Add operation
        op = self.add_operation(
            "edit",
            file_path,
            backup_path=backup_path,
            old_content=old_content,
            new_content=new_content
        )

        # Execute edit
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        op.executed = True

        return {
            "operation": "edit",
            "path": str(file_path),
            "backed_up": True
        }

    def commit(self):
        """Commit all operations (makes changes permanent)."""
        if self.committed:
            return

        # All operations already executed during add
        # Just mark as committed so rollback won't happen
        self.committed = True

    def rollback(self):
        """Rollback all operations (restore from backups)."""
        if self.rolled_back:
            return

        # Reverse operations in reverse order
        for op in reversed(self.operations):
            if not op.executed:
                continue

            try:
                if op.op_type == "move":
                    # Move back from destination to source
                    if op.destination and op.destination.exists():
                        if op.backup_path and op.backup_path.exists():
                            shutil.move(str(op.destination), str(op.file_path))
                    elif op.backup_path and op.backup_path.exists():
                        # Restore from backup
                        shutil.copy2(str(op.backup_path), str(op.file_path))

                elif op.op_type == "delete":
                    # Restore from backup
                    if op.backup_path and op.backup_path.exists():
                        shutil.copy2(str(op.backup_path), str(op.file_path))

                elif op.op_type in ["write", "edit"]:
                    # Restore from backup or delete if new file
                    if op.backup_path and op.backup_path.exists():
                        shutil.copy2(str(op.backup_path), str(op.file_path))
                    elif op.old_content is None:
                        # Was a new file, delete it
                        if op.file_path.exists():
                            op.file_path.unlink()

            except Exception as e:
                # Log rollback error but continue
                print(f"Warning: Failed to rollback {op.op_type} on {op.file_path}: {e}")

        self.rolled_back = True

    def _resolve_path(self, path: str) -> Path:
        """Resolve path relative to cwd."""
        p = Path(path)
        if not p.is_absolute():
            p = self.cwd / p
        return p.resolve()

    def _create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file in the backup directory."""
        if not self.backup_dir:
            raise RuntimeError("Transaction not started")

        # Create backup with same relative structure
        rel_path = file_path.relative_to(self.cwd) if file_path.is_relative_to(self.cwd) else file_path.name
        backup_path = self.backup_dir / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(str(file_path), str(backup_path))
        return backup_path

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of transaction operations."""
        return {
            "total_operations": len(self.operations),
            "executed": sum(1 for op in self.operations if op.executed),
            "committed": self.committed,
            "rolled_back": self.rolled_back,
            "operations": [
                {
                    "type": op.op_type,
                    "file": str(op.file_path),
                    "executed": op.executed
                }
                for op in self.operations
            ]
        }
