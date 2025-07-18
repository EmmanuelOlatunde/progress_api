from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from progress.models import Task, Category
from progress.filters import TaskFilter

User = get_user_model()

class TaskFilterTests(TestCase):
    def setUp(self):
        """Create sample user, categories, and tasks"""
        self.user = User.objects.create_user(username="tester", password="pass1234")

        self.cat_dev = Category.objects.create(name="Development")
        self.cat_docs = Category.objects.create(name="Documentation")
        self.cat_frontend = Category.objects.create(name="Frontend")

        self.task1 = Task.objects.create(
            user=self.user,
            title="Write Django Tests",
            description="Write unit tests for filters",
            category=self.cat_dev,
            priority="high",
            difficulty="hard",
            is_completed=False,
        )

        self.task2 = Task.objects.create(
            user=self.user,
            title="Fix CSS Bug",
            description="Fix styling issue on dashboard",
            category=self.cat_frontend,
            priority="medium",
            difficulty="medium",
            is_completed=True,
            completed_at=timezone.now(),
        )

        self.task3 = Task.objects.create(
            user=self.user,
            title="Update Docs",
            description="Add filtering docs",
            category=self.cat_docs,
            priority="low",
            difficulty="easy",
            is_completed=False,
        )

    def assertTasksEqual(self, qs, expected_tasks):
        """Helper: Compare queryset results with expected task list"""
        self.assertEqual(list(qs.order_by("id")), expected_tasks)

    def test_filter_by_category(self):
        filterset = TaskFilter(
            data={"category": self.cat_dev.id},
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task1])

    def test_filter_by_priority_case_insensitive(self):
        filterset = TaskFilter(
            data={"priority": "LOW"},
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task3])

    def test_filter_by_is_completed_true(self):
        filterset = TaskFilter(
            data={"is_completed": True},
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task2])

    def test_filter_by_is_completed_false(self):
        filterset = TaskFilter(
            data={"is_completed": False},
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task1, self.task3])

    def test_filter_by_difficulty(self):
        filterset = TaskFilter(
            data={"difficulty": "hard"},
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task1])

    def test_filter_by_search_title(self):
        filterset = TaskFilter(
            data={"search": "docs"},  # matches task3 title
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task3])

    def test_filter_by_search_description(self):
        filterset = TaskFilter(
            data={"search": "styling issue"},  # matches task2 description
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task2])

    def test_combined_filters(self):
        filterset = TaskFilter(
            data={
                "search": "Write",
                "category": self.cat_dev.id,
                "difficulty": "hard"
            },
            queryset=Task.objects.all()
        )
        self.assertTasksEqual(filterset.qs, [self.task1])

    def test_empty_filter_returns_all(self):
        filterset = TaskFilter(data={}, queryset=Task.objects.all())
        self.assertTasksEqual(filterset.qs, [self.task1, self.task2, self.task3])
