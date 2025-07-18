from django.urls import path
from rest_framework.test import APITestCase, APIClient
from rest_framework.views import APIView
from progress.pagination import CustomPageNumberPagination
from progress.models import Category
from django.contrib.auth import get_user_model
from django.test import override_settings


# --- Dummy view for testing ---
class CategoryListView(APIView):
    pagination_class = CustomPageNumberPagination

    def get(self, request):
        queryset = Category.objects.all().order_by("id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(
            [{"id": c.id, "name": c.name} for c in page]
        )

urlpatterns = [
    path("test-pagination/", CategoryListView.as_view(), name="test-pagination"),
]
User = get_user_model()

@override_settings(ROOT_URLCONF=__name__)
class CustomPaginationTests(APITestCase):
    def setUp(self):
        """Setup authenticated client and sample categories"""
        self.user = User.objects.create_user(username="tester", password="pass1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)  # ✅ Authenticated client

        self.total_items = 55
        self.categories = [
            Category.objects.create(name=f"Category {i}") for i in range(self.total_items)
        ]


    def test_default_page_size_20(self):
        """Default pagination should return 20 items per page"""
        response = self.client.get("/test-pagination/")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should have count == 55
        self.assertEqual(data["count"], self.total_items)
        # Default page size
        self.assertEqual(len(data["results"]), 20)

        # next should exist, previous should be None
        self.assertIsNotNone(data["next"])
        self.assertIsNone(data["previous"])

    def test_second_page_returns_next_batch(self):
        """Page=2 should return next 20 items"""
        response = self.client.get("/test-pagination/?page=2")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["count"], self.total_items)
        self.assertEqual(len(data["results"]), 20)
        self.assertIsNotNone(data["next"])
        self.assertIsNotNone(data["previous"])  # page 2 has a previous

        # Verify first item is Category 20 (0-based index -> Category 21)
        first_item_name = data["results"][0]["name"]
        self.assertEqual(first_item_name, "Category 20")

    def test_last_page_has_remaining_items(self):
        """Last page should have remaining 15 items"""
        response = self.client.get("/test-pagination/?page=3")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Last page has only remaining 15
        self.assertEqual(len(data["results"]), 15)
        self.assertIsNone(data["next"])  # no next page
        self.assertIsNotNone(data["previous"])

    def test_override_page_size_query_param(self):
        """page_size query param should allow client to request custom size"""
        response = self.client.get("/test-pagination/?page_size=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Now only 10 per page
        self.assertEqual(len(data["results"]), 10)
        self.assertEqual(data["count"], self.total_items)
        self.assertIsNotNone(data["next"])

    def test_max_page_size_cap(self):
        """page_size beyond max_page_size=100 should be capped"""
        response = self.client.get("/test-pagination/?page_size=5000")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should cap at max_page_size (100)
        self.assertEqual(len(data["results"]), 55)  # Only 55 exist
        self.assertIsNone(data["next"])  # all items fit in one page

    def test_invalid_page_returns_error(self):
        """Invalid page number should return 404"""
        response = self.client.get("/test-pagination/?page=999")
        self.assertEqual(response.status_code, 404)

    def test_combination_page_and_custom_size(self):
        """Should correctly handle both page & page_size together"""
        response = self.client.get("/test-pagination/?page=2&page_size=15")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # page_size=15 → first page has 15, second page also has 15
        self.assertEqual(len(data["results"]), 15)
        self.assertEqual(data["count"], self.total_items)
        self.assertIsNotNone(data["next"])
        self.assertIsNotNone(data["previous"])
