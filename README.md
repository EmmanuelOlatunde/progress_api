# 📈 progress\_api — Gamify Your Daily Productivity

Welcome to **Progress API**, a Django-powered backend designed to gamify your life. Log tasks, earn XP, unlock achievements, and visualize your progress with rich stats, all while leveling up your productivity in real-time.

---

## 🚀 Features

| Module                | Description                                                                      |
| --------------------- | -------------------------------------------------------------------------------- |
| ✅ **User Auth**       | Secure authentication using JWT with registration, login, logout, password reset |
| ✅ **Task System**     | Create, update, delete, and complete tasks with XP rewards                       |
| ✅ **XP & Levels**     | Earn XP and level up automatically as you complete tasks                         |
| ✅ **Achievements**    | Unlock badges and milestones for your productivity                               |
| ✅ **Statistics**      | Analyze your activity, task performance, streaks, and categories                 |
| ✅ **Weekly Reviews**  | Reflect weekly with summaries and top categories                                 |
| ✅ **Public Profiles** | Share your progress or keep it private                                           |
| ✅ **Admin Tools**     | Full CRUD for users and profiles (admin only)                                    |
| ✅ **Gamified UX**     | Missions, leaderboards, notifications, and streaks                               |

---

## 🛠️ Tech Stack

| Layer       | Tool/Framework            |
| ----------- | ------------------------- |
| Backend     | Django REST Framework     |
| Auth        | Djoser + SimpleJWT        |
| Database    | PostgreSQL                |
| Deployment  | Render / Railway / Heroku |
| Optional FE | React.js / Next.js / HTMX |

---

## 🔑 API Authentication

This API uses **JWT (access + refresh tokens)** for authentication. Use the following endpoints to manage auth:

```http
POST /api/auth/register/         # Register new user
POST /api/auth/login/            # Login (returns access + refresh)
POST /api/auth/logout/           # Logout (blacklists token)
POST /api/auth/token/refresh/    # Refresh access token
GET  /api/auth/me/               # Authenticated user info
```

---

## 📦 Project Structure

```
progress_api/
│
├── config/               # Django project settings
├── progress/             # Main gamification app (Tasks, XP, Stats)
├── achievements/         # Achievement unlock logic (optional)
├── users/                # User auth, profile, public info
├── static/               # Static files
├── templates/            # For browsable API or frontend
└── tests/                # Global & unit test coverage
```

---

## 🔧 Setup Instructions

```bash
# 1. Clone the repo
git clone https://github.com/EmmanuelOlatunde/progress_api.git
cd progress_api

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add a `.env` file with secrets (e.g. DB, JWT, email config)

# 5. Apply migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create default data
python manage.py create_default_categories
python manage.py create_default_achievements

# 7. Create a superuser
python manage.py createsuperuser

# 8. Run the server
python manage.py runserver
```

---

## 📘 Example API Usage

### ✅ Register a New User

```json
POST /api/auth/register/
{
  "username": "User1",
  "email": "user1@example.com",
  "password": "strongPassword123",
  "password_confirm": "strongPassword123",
  "first_name": "User",
  "last_name": "One"
}
```

### ✅ Create a Task

```json
POST /api/tasks/
{
  "title": "Write blog post",
  "description": "Draft the next article on productivity",
  "category": 1,
  "difficulty": "medium",
  "priority": "high",
  "due_date": "2024-12-31T23:59:59Z"
}
```

### ✅ Complete Task (gain XP)

```http
PATCH /api/tasks/1/complete/
```

---

## 📊 Stats & Progress

| Feature        | Endpoint                                |
| -------------- | --------------------------------------- |
| XP Logs        | `GET /api/xp/`                          |
| Level Info     | `GET /api/xp/level/`                    |
| Stats          | `GET /api/stats/`                       |
| Streaks        | `GET /api/stats/streaks/`               |
| Achievements   | `GET /api/achievements/unlocked/`       |
| Weekly Reviews | `GET /api/weekly-reviews/current_week/` |

---

## 🔐 Admin & Profiles

* `GET /api/users/` – List users (admin)
* `GET /api/profile/` – Get current profile
* `POST /api/profile/avatar/` – Upload avatar
* `GET /api/profile/{username}/` – Public profile

---

## 🚧 To-Do / Roadmap

* [ ] Mission Generator System
* [ ] Notification System Integration
* [ ] API Rate Limiting & Throttling
* [ ] Public Leaderboard Rankings
* [ ] Email verification for new users

---


## 🤝 Contributing

Pull requests are welcome! Please fork the repo and submit a PR with meaningful commit messages.

---

## 📜 License

This project is open-source and available under the MIT License.

---

## 🌐 Links

* **Live API Demo**: *(Coming soon)*
* **Frontend **: *(Coming soon)*
* **Author**: [@EmmanuelOlatunde](https://github.com/EmmanuelOlatunde)

---
>>>>>>> d999e4840504927acc4ffbec98bb95ef713ed687
