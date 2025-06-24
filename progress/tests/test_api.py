from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Category, Task
from django.contrib.auth import get_user_model

User = get_user_model()

class TaskAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        self.client.force_authenticate(user=self.user)

    def test_create_task(self):
        url = reverse('task-list')
        data = {
            'title': 'New Task',
            'description': 'A new test task',
            'category': self.category.id,
            'difficulty': 'medium',
            'priority': 'high'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get().title, 'New Task')

    def test_complete_task(self):
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            category=self.category
        )
        
        url = reverse('task-complete', kwargs={'pk': task.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertTrue(task.is_completed)

    def test_task_filtering(self):
        # Create tasks with different properties
        Task.objects.create(
            user=self.user,
            title='Easy Task',
            category=self.category,
            difficulty='easy'
        )
        Task.objects.create(
            user=self.user,
            title='Hard Task',
            category=self.category,
            difficulty='hard'
        )
        
        # Filter by difficulty
        url = reverse('task-list') + '?difficulty=easy'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Easy Task')

class XPAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_xp_summary(self):
        url = reverse('xp-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile', response.data)
        self.assertIn('recent_activity', response.data)

    def test_level_info(self):
        url = reverse('xp-level')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_level', response.data)
        self.assertIn('total_xp', response.data)
        self.assertIn('progress_percentage', response.data)
