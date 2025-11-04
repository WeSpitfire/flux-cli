#!/usr/bin/env python3
"""Test Workspace Intelligence - Session management, task tracking, and summaries."""

import tempfile
import time
from pathlib import Path
    Workspace, Task, WorkSession, TaskPriority, TaskStatus
)


def test_workspace_intelligence():
    """Test all workspace intelligence features."""

    print("🧪 Testing Workspace Intelligence\n")
    print("=" * 60)

    # Create temporary workspace directory
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_dir = Path(tmpdir) / "workspace"
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()

        workspace = Workspace(workspace_dir, project_dir)

        # Test 1: Session Creation
        print("\n1️⃣  Test: Session Creation")
        session = workspace.create_session("Test Session", "Testing workspace features")

        assert session.name == "Test Session"
        assert session.description == "Testing workspace features"
        assert session.project_path == str(project_dir)
        assert session.time_spent_seconds == 0.0
        assert len(session.files_modified) == 0

        print(f"   ✓ Created session: {session.name}")
        print(f"     ID: {session.id}")

        # Test 2: Session Save and Restore
        print("\n2️⃣  Test: Session Save and Restore")

        # Save session
        saved_session = workspace.save_session("Saved Work", "My saved work")
        session_id = saved_session.id

        # Simulate some work
        time.sleep(0.1)
        workspace.track_file_access("test.py")
        workspace.track_file_access("main.py")
        workspace.track_command("pytest")
        workspace.track_command("git status")

        # Save again to update
        workspace.save_session("Saved Work", "My saved work")

        # End session
        workspace.end_session()

        assert workspace.active_session is None
        print("   ✓ Session saved and ended")

        # Restore session
        restored = workspace.restore_session(session_id)
        assert restored is not None
        assert restored.name == "Saved Work"
        assert len(restored.files_modified) == 2
        assert "test.py" in restored.files_modified
        assert "pytest" in restored.recent_commands

        print(f"   ✓ Restored session: {restored.name}")
        print(f"     Files: {len(restored.files_modified)}")
        print(f"     Commands: {len(restored.recent_commands)}")

        # Test 3: Task Creation
        print("\n3️⃣  Test: Task Creation")

        task1 = workspace.create_task(
            "Implement feature X",
            description="Add new feature with tests",
            priority=TaskPriority.HIGH,
            estimated_minutes=120,
            tags=["feature", "backend"],
            related_files=["api.py", "models.py"]
        )

        assert task1.title == "Implement feature X"
        assert task1.priority == TaskPriority.HIGH
        assert task1.status == TaskStatus.TODO
        assert task1.estimated_minutes == 120
        assert "feature" in task1.tags
        assert "api.py" in task1.related_files

        print(f"   ✓ Created task: {task1.title}")
        print(f"     Priority: {task1.priority.value}")
        print(f"     Tags: {task1.tags}")

        # Create more tasks
        task2 = workspace.create_task(
            "Fix bug in login",
            priority=TaskPriority.URGENT,
            tags=["bug", "security"]
        )

        task3 = workspace.create_task(
            "Update documentation",
            priority=TaskPriority.MEDIUM,
            tags=["docs"]
        )

        task4 = workspace.create_task(
            "Refactor old code",
            priority=TaskPriority.LOW,
            tags=["refactor"]
        )

        print(f"   ✓ Created 4 tasks total")

        # Test 4: Task Updates
        print("\n4️⃣  Test: Task Updates")

        # Mark task as in progress
        updated = workspace.update_task(task1.id, status=TaskStatus.IN_PROGRESS)
        assert updated.status == TaskStatus.IN_PROGRESS
        print(f"   ✓ Marked task as IN_PROGRESS: {updated.title}")

        # Complete task
        workspace.update_task(task2.id, status=TaskStatus.DONE)
        completed_task = workspace.get_task(task2.id)
        assert completed_task.status == TaskStatus.DONE
        assert completed_task.completed_at is not None
        print(f"   ✓ Completed task: {completed_task.title}")

        # Test 5: Task Listing and Filtering
        print("\n5️⃣  Test: Task Listing and Filtering")

        # List all tasks
        all_tasks = workspace.list_tasks()
        assert len(all_tasks) == 4
        print(f"   ✓ Listed all tasks: {len(all_tasks)}")

        # Filter by status
        todo_tasks = workspace.list_tasks(status=TaskStatus.TODO)
        assert len(todo_tasks) == 2  # task3 and task4
        print(f"   ✓ TODO tasks: {len(todo_tasks)}")

        done_tasks = workspace.list_tasks(status=TaskStatus.DONE)
        assert len(done_tasks) == 1  # task2
        print(f"   ✓ DONE tasks: {len(done_tasks)}")

        # Filter by priority
        high_priority = workspace.list_tasks(priority=TaskPriority.HIGH)
        assert len(high_priority) == 1  # task1
        print(f"   ✓ HIGH priority tasks: {len(high_priority)}")

        # Filter by tags
        docs_tasks = workspace.list_tasks(tags=["docs"])
        assert len(docs_tasks) == 1  # task3
        print(f"   ✓ Tasks with 'docs' tag: {len(docs_tasks)}")

        # Test 6: AI-Powered Task Suggestion
        print("\n6️⃣  Test: AI-Powered Task Suggestion")

        suggested = workspace.suggest_next_task()
        assert suggested is not None

        # Should suggest task1 (HIGH priority, IN_PROGRESS)
        # or task3/task4 depending on scoring
        print(f"   ✓ AI suggested next task: {suggested.title}")
        print(f"     Priority: {suggested.priority.value}")
        print(f"     Status: {suggested.status.value}")

        # Task scoring validation
        # URGENT task (if not done) should have highest score
        # But task2 is DONE, so next should be HIGH priority task1
        assert suggested.id in [task1.id, task3.id, task4.id]

        # Test 7: Current Task Tracking
        print("\n7️⃣  Test: Current Task Tracking")

        workspace.set_current_task(task1.id)
        assert workspace.active_session.current_task_id == task1.id

        # Task should now be IN_PROGRESS (if it wasn't already)
        current_task = workspace.get_task(task1.id)
        assert current_task.status == TaskStatus.IN_PROGRESS

        print(f"   ✓ Set current task: {current_task.title}")

        # Test 8: Work Summary Generation
        print("\n8️⃣  Test: Work Summary Generation")

        # Simulate some work time
        time.sleep(0.1)
        workspace.track_file_access("feature.py")
        workspace.track_file_access("test_feature.py")
        workspace.track_command("pytest tests/")

        # End session to get summary
        summary = workspace.end_session()

        assert summary is not None
        assert summary.session_name == "Saved Work"
        assert summary.duration_minutes > 0
        assert len(summary.files_modified) >= 2
        assert summary.commands_executed >= 2
        assert len(summary.tasks_completed) == 1  # task2 was completed
        assert "Fix bug in login" in summary.tasks_completed

        print(f"   ✓ Generated work summary")
        print(f"     Duration: {summary.duration_minutes:.2f} minutes")
        print(f"     Files: {len(summary.files_modified)}")
        print(f"     Commands: {summary.commands_executed}")
        print(f"     Tasks completed: {len(summary.tasks_completed)}")

        if summary.key_achievements:
            print(f"     Achievements: {len(summary.key_achievements)}")

        # Test 9: Daily Summary
        print("\n9️⃣  Test: Daily Summary")

        daily = workspace.get_daily_summary()

        assert daily['sessions'] >= 1
        assert daily['files_modified'] >= 2
        assert daily['tasks_completed'] == 1
        assert "Fix bug in login" in daily['completed_task_titles']

        print(f"   ✓ Daily summary generated")
        print(f"     Sessions: {daily['sessions']}")
        print(f"     Time: {daily['total_minutes']:.2f} minutes")
        print(f"     Files: {daily['files_modified']}")
        print(f"     Tasks: {daily['tasks_completed']}")

        # Test 10: Session Persistence
        print("\n🔟 Test: Session Persistence")

        # Create new workspace instance (simulates restart)
        workspace2 = Workspace(workspace_dir, project_dir)

        # Should load saved sessions
        loaded_sessions = workspace2.list_sessions()
        assert len(loaded_sessions) >= 1
        print(f"   ✓ Loaded {len(loaded_sessions)} session(s) from disk")

        # Should load saved tasks
        loaded_tasks = workspace2.list_tasks()
        assert len(loaded_tasks) == 4
        print(f"   ✓ Loaded {len(loaded_tasks)} task(s) from disk")

        # Verify task data persisted correctly
        loaded_task1 = workspace2.get_task(task1.id)
        assert loaded_task1.title == "Implement feature X"
        assert loaded_task1.priority == TaskPriority.HIGH
        assert loaded_task1.status == TaskStatus.IN_PROGRESS

        print(f"   ✓ Task data persisted correctly")

        # Test 11: Task Deletion
        print("\n1️⃣1️⃣  Test: Task Deletion")

        deleted = workspace2.delete_task(task4.id)
        assert deleted is True

        remaining = workspace2.list_tasks()
        assert len(remaining) == 3
        assert task4.id not in [t.id for t in remaining]

        print(f"   ✓ Deleted task: {task4.title}")
        print(f"     Remaining tasks: {len(remaining)}")

        # Test 12: Session Deletion
        print("\n1️⃣2️⃣  Test: Session Deletion")

        sessions_before = workspace2.list_sessions()
        session_to_delete = sessions_before[0].id

        deleted = workspace2.delete_session(session_to_delete)
        assert deleted is True

        sessions_after = workspace2.list_sessions()
        assert len(sessions_after) == len(sessions_before) - 1

        print(f"   ✓ Deleted session")
        print(f"     Remaining sessions: {len(sessions_after)}")

        # Test 13: Priority-Based Sorting
        print("\n1️⃣3️⃣  Test: Priority-Based Task Sorting")

        # Create tasks with different priorities
        urgent_task = workspace2.create_task("Critical bug", priority=TaskPriority.URGENT)
        low_task = workspace2.create_task("Nice to have", priority=TaskPriority.LOW)

        sorted_tasks = workspace2.list_tasks()

        # First task should be URGENT
        assert sorted_tasks[0].priority == TaskPriority.URGENT

        # Last tasks should be lower priority
        priorities = [t.priority for t in sorted_tasks]
        print(f"   ✓ Tasks sorted by priority:")
        for i, task in enumerate(sorted_tasks[:5], 1):
            print(f"     {i}. {task.title} [{task.priority.value}]")

        # Test 14: Context Tracking
        print("\n1️⃣4️⃣  Test: Context Tracking")

        # Start new session
        workspace2.save_session("Context Test")

        # Track various activities
        files = ["main.py", "utils.py", "config.py", "test.py"]
        for f in files:
            workspace2.track_file_access(f)

        commands = ["git status", "pytest", "black .", "git commit"]
        for cmd in commands:
            workspace2.track_command(cmd)

        session = workspace2.active_session
        assert len(session.files_modified) == 4
        assert len(session.recent_commands) == 4
        assert session.commands_run == 4

        print(f"   ✓ Context tracked:")
        print(f"     Files: {len(session.files_modified)}")
        print(f"     Commands: {len(session.recent_commands)}")

        # Verify recent commands limit (20)
        for i in range(25):
            workspace2.track_command(f"command_{i}")

        assert len(workspace2.active_session.recent_commands) == 20
        print(f"   ✓ Recent commands limited to 20")

    print("\n" + "=" * 60)
    print("✅ All Workspace Intelligence tests passed!")
    print("\nKey Features Validated:")
    print("  • Session save/restore with complete context")
    print("  • Task creation with priorities and tags")
    print("  • Task updates and status tracking")
    print("  • Task filtering by status, priority, tags")
    print("  • AI-powered next task suggestion")
    print("  • Work summary generation")
    print("  • Daily summary aggregation")
    print("  • Session and task persistence")
    print("  • Context tracking (files, commands)")
    print("  • Priority-based task sorting")
    print("  • Time tracking automation")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_workspace_intelligence()
