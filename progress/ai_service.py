import json
import logging
import requests
from django.utils import timezone
from django.db import models as django_models
from datetime import timedelta
from decouple import config
from typing import List, Dict, Optional
from .models import Task, ProgressProfile, UserMission, Category

logger = logging.getLogger(__name__)

GROQ_API_KEY = config('GROQ_API_KEY', default='')
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

VALID_MISSION_TYPES = [
    'task_count', 'category_focus', 'streak',
    'timing', 'difficulty', 'xp_target',
    'daily_goal', 'weekly_challenge'
]
VALID_DIFFICULTIES = ['easy', 'medium', 'hard', 'legendary']

# Rate limit: one AI generation per user per hour
AI_GENERATION_COOLDOWN_MINUTES = 60


class AIMissionService:
    def __init__(self, user):
        self.user = user

    # ─── Rate Limiting ────────────────────────────────────────────────────────

    def check_rate_limit(self) -> Optional[str]:
        """
        Returns an error string if user is rate limited, None if they're clear.
        Uses a simple Notification record as a lightweight timestamp store
        — no Redis or cache needed.
        """
        cutoff = timezone.now() - timedelta(minutes=AI_GENERATION_COOLDOWN_MINUTES)
        recent = (
            # Reuse Notification model as a cheap timestamp log
            # We create one when generation succeeds, check it here
        )
        # Use XPLog as the timestamp store — look for a 'bonus' log with our marker
        from .models import XPLog
        recent_generation = XPLog.objects.filter(
            user=self.user,
            action='bonus',
            description='__ai_mission_generation__',
            created_at__gte=cutoff
        ).exists()

        if recent_generation:
            return f'AI generation is available once per hour. Please wait before generating again.'
        return None

    def _record_generation(self):
        """Record that a generation happened for rate limiting purposes."""
        from .models import XPLog
        XPLog.objects.create(
            user=self.user,
            action='bonus',
            xp_earned=0,
            description='__ai_mission_generation__'
        )

    # ─── Context Gathering ────────────────────────────────────────────────────

    def _gather_user_context(self) -> Dict:

        profile, _ = ProgressProfile.objects.get_or_create(user=self.user)
        last_30_days = timezone.now() - timedelta(days=30)

        recent_tasks = Task.objects.filter(user=self.user, created_at__gte=last_30_days)
        completed_recent = recent_tasks.filter(is_completed=True)

        # Top 3 categories by completion count this month
        top_categories = (
            completed_recent
            .values('category__name')
            .annotate(count=django_models.Count('id'))
            .order_by('-count')[:3]
        )
        top_category_names = [
            c['category__name'] for c in top_categories
            if c['category__name']
        ]

        # All categories
        all_category_names = list(Category.objects.values_list('name', flat=True))

        # Categories with zero completions this month
        active_category_names = set(
            completed_recent
            .values_list('category__name', flat=True)
            .distinct()
        )
        zero_categories = [
            c for c in all_category_names
            if c not in active_category_names
        ]

        # Completion rate per difficulty
        difficulty_stats = {}
        for diff in ['easy', 'medium', 'hard', 'expert']:
            total = recent_tasks.filter(difficulty=diff).count()
            done = completed_recent.filter(difficulty=diff).count()
            difficulty_stats[diff] = {
                'total': total,
                'completed': done,
                'rate': round((done / total * 100), 1) if total > 0 else 0,
            }

        # Active mission types — avoid duplicating
        active_template_types = list(
            UserMission.objects.filter(user=self.user, status='active')
            .exclude(template=None)
            .values_list('template__mission_type', flat=True)
            .distinct()
        )

        return {
            'level': profile.current_level,
            'total_xp': profile.total_xp,
            'current_streak': profile.current_streak,
            'longest_streak': profile.longest_streak,
            'punctuality_rate': profile.punctuality_rate,
            'top_categories': top_category_names,
            'zero_categories': zero_categories[:3],
            'all_categories': all_category_names,
            'difficulty_stats': difficulty_stats,
            'active_mission_types': active_template_types,
            'total_completed_30d': completed_recent.count(),
        }

    # ─── Prompt Building ──────────────────────────────────────────────────────

    def _build_prompt(self, context: Dict) -> str:
        strengths = (
            ', '.join(context['top_categories'])
            if context['top_categories'] else 'no strong categories yet'
        )
        growth_areas = (
            ', '.join(context['zero_categories'])
            if context['zero_categories'] else 'none identified'
        )
        avoid_types = (
            ', '.join(context['active_mission_types'])
            if context['active_mission_types'] else 'none'
        )
        all_cats = (
            ', '.join(context['all_categories'])
            if context['all_categories'] else 'General'
        )

        return f"""Generate exactly 3 personalized productivity missions for this user.

USER STATS:
- Level: {context['level']}
- Total XP: {context['total_xp']}
- Current streak: {context['current_streak']} days
- Longest streak: {context['longest_streak']} days
- Punctuality rate: {context['punctuality_rate']}%
- Tasks completed last 30 days: {context['total_completed_30d']}
- Strong categories: {strengths}
- Growth areas (no activity): {growth_areas}
- Difficulty stats: {json.dumps(context['difficulty_stats'])}

AVAILABLE CATEGORIES (use exact names or null): {all_cats}
MISSION TYPES TO AVOID (already active): {avoid_types}

STRICT RULES:
- Return ONLY a valid JSON array. No markdown. No code blocks. No explanation.
- Exactly 3 missions.
- mission_type must be one of: task_count, category_focus, streak, timing, difficulty, xp_target
- difficulty must be one of: easy, medium, hard, legendary
- target_value: integer between 1 and 50
- xp_reward: integer between 50 and 500
- duration_days: integer between 1 and 14
- category: exact name from AVAILABLE CATEGORIES above, or null
- At least 1 mission must target a growth area if any exist
- Do not use mission types listed under MISSION TYPES TO AVOID

OUTPUT FORMAT — JSON array only, nothing else:
[
  {{
    "title": "Short mission title",
    "description": "Clear description of what to do",
    "mission_type": "task_count",
    "difficulty": "medium",
    "target_value": 5,
    "xp_reward": 150,
    "duration_days": 7,
    "category": "Fitness",
    "reasoning": "One sentence explaining why this fits this user"
  }}
]"""

    # ─── API Call ─────────────────────────────────────────────────────────────

    def _call_openrouter(self, prompt: str) -> Optional[List[Dict]]:
        if not GROQ_API_KEY:
            logger.error('GROQ_API_KEY not set in .env')
            return None

        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json',
        }

        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are a gamification expert. '
                        'You ONLY respond with valid JSON arrays. '
                        'No markdown. No code blocks. No explanation. JSON only.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.7,
            'max_tokens': 1200,
            'response_format': {'type': 'json_object'},  # enforces JSON
        }

        try:
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            raw = data['choices'][0]['message']['content'].strip()
            parsed = json.loads(raw)

            # Groq json_object mode returns a dict, not a list — unwrap if needed
            if isinstance(parsed, dict):
                parsed = parsed.get('missions', list(parsed.values())[0] if parsed else [])

            if not isinstance(parsed, list):
                logger.error(f'AI returned non-list: {type(parsed)}')
                return None

            return parsed

        except requests.exceptions.Timeout:
            logger.error('Groq timed out after 30s')
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f'Groq HTTP error: {e.response.status_code} {e.response.text}')
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f'Groq request failed: {e}')
            return None
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f'Failed to parse Groq response: {e}')
            return None


    # ─── Validation ───────────────────────────────────────────────────────────

    def _validate_mission(self, raw: Dict) -> Optional[Dict]:
        """
        Validate and sanitize one AI mission dict.
        Returns None if unfixable. Never trusts raw AI output.
        """
        from .models import Category

        if not isinstance(raw, dict):
            return None

        title = str(raw.get('title', '')).strip()[:100]
        if not title:
            return None

        description = str(raw.get('description', '')).strip()[:200]
        if not description:
            description = title

        mission_type = raw.get('mission_type', 'task_count')
        if mission_type not in VALID_MISSION_TYPES:
            mission_type = 'task_count'

        difficulty = raw.get('difficulty', 'medium')
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = 'medium'

        try:
            target_value = max(1, min(50, int(raw.get('target_value', 5))))
        except (ValueError, TypeError):
            target_value = 5

        try:
            xp_reward = max(50, min(500, int(raw.get('xp_reward', 100))))
        except (ValueError, TypeError):
            xp_reward = 100

        try:
            duration_days = max(1, min(14, int(raw.get('duration_days', 7))))
        except (ValueError, TypeError):
            duration_days = 7

        # Validate category against DB — null if AI hallucinated one
        category_name = raw.get('category')
        category_id = None
        if category_name and isinstance(category_name, str):
            cat = Category.objects.filter(name__iexact=category_name.strip()).first()
            if cat:
                category_id = cat.id
                category_name = cat.name
            else:
                category_name = None

        reasoning = str(raw.get('reasoning', '')).strip()[:150]

        return {
            'title': title,
            'description': description,
            'mission_type': mission_type,
            'difficulty': difficulty,
            'target_value': target_value,
            'xp_reward': xp_reward,
            'duration_days': duration_days,
            'category': category_name,
            'category_id': category_id,
            'reasoning': reasoning,
        }

    # ─── Public API ───────────────────────────────────────────────────────────

    def generate_preview(self) -> Dict:
        """
        Generate 3 AI missions and return validated preview data.
        Nothing is saved to the DB — preview only.
        """
        context = self._gather_user_context()
        prompt = self._build_prompt(context)
        raw_missions = self._call_openrouter(prompt)

        if raw_missions is None:
            return {
                'missions': [],
                'error': 'AI generation failed. Please try again in a moment.',
            }

        validated = []
        for raw in raw_missions:
            result = self._validate_mission(raw)
            if result:
                validated.append(result)

        if not validated:
            return {
                'missions': [],
                'error': 'AI returned unusable data. Please try again.',
            }

        # Record for rate limiting only after we have valid results
        self._record_generation()

        return {
            'missions': validated[:3],
            'error': None,
        }

    def save_mission(self, mission_data: Dict) -> 'UserMission':
        """
        Validate and save one AI mission the user accepted.
        Re-validates server-side — never trusts frontend data directly.
        Raises ValueError if invalid or limit reached.
        """

        validated = self._validate_mission(mission_data)
        if not validated:
            raise ValueError('Invalid mission data.')

        active_count = UserMission.objects.filter(
            user=self.user, status='active'
        ).count()
        if active_count >= 5:
            raise ValueError('Maximum of 5 active missions reached.')

        category = None
        if validated['category_id']:
            category = Category.objects.filter(id=validated['category_id']).first()

        mission = UserMission.objects.create(
            user=self.user,
            template=None,                    # AI missions have no template
            mission_type=validated['mission_type'],  # Store mission_type for progress updates
            title=validated['title'],
            description=validated['description'],
            target_value=validated['target_value'],
            xp_reward=validated['xp_reward'],
            bonus_multiplier=1.0,
            category=category,
            end_date=timezone.now() + timedelta(days=validated['duration_days']),
            status='active',
        )

        return mission