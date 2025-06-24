// API Configuration
const API_BASE_URL = window.location.origin; // Use current origin
const API_ENDPOINTS = {
    auth: {
        login: '/api/auth/login/',  // Added /api prefix
        register: '/api/auth/register/',
        logout: '/api/auth/logout/',
        me: '/api/auth/me/',
        refresh: '/api/auth/token/refresh/'
    },
    tasks: '/api/tasks/',
    categories: '/api/categories/',
    achievements: '/api/achievements/',
    weeklyReviews: '/api/weekly-reviews/',
    xp: '/api/xp/',
    profile: '/api/profile/',
    stats: '/api/stats/'
};

// Global State
let currentUser = null;
let authToken = null;
let refreshToken = null;
let currentSection = 'overview';
let currentCategoryFilter = 'all';
let currentStatusFilter = 'all';
let currentPriorityFilter = 'all'

// Utility Functions
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    // Create default configuration
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        }
    };

    // Add authorization if token exists
    if (authToken) {
        defaultOptions.headers['Authorization'] = `Bearer ${authToken}`;
    }

    const csrftoken = getCSRFToken();
    if (csrftoken) {
        defaultOptions.headers['X-CSRFToken'] = csrftoken;
    }

    // Merge options with defaults
    const config = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

        try {
        showLoading();
        const response = await fetch(url, config);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Handle HTML responses and 204 No Content
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            // Handle 204 No Content for successful DELETE operations
            if (response.status === 204) {
                return; // Successfully processed, no content expected
            }
            const text = await response.text();
            throw new Error(`Invalid response: ${text.slice(0, 100)}`);
        }

     return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showToast(error.message || 'An error occurred', 'error');
        throw error;
    } finally {
        hideLoading();
    }


    // Add this helper function
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

async function refreshAuthToken() {
    if (!refreshToken) return false;
    
    try {
        const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.auth.refresh}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            authToken = data.access;
            localStorage.setItem('authToken', authToken);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }
    
    return false;
}

// Authentication Functions
async function login(email, password) {
        try {

        
        const response = await fetch(API_ENDPOINTS.auth.login, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        

        
        const data = await response.json();

         // --- THIS IS THE CRITICAL PART TO REVIEW ---
        // If your server sends a 200 OK but includes an 'error' or 'success: false' field
        // you need to handle it here.
        if (data.error || data.success === false) {
            showToast(data.message || 'Login failed. Please check your credentials.', 'error');
            return;
        }
        // --- END CRITICAL PART ---
        authToken = data.access;
        refreshToken = data.refresh;
        
        localStorage.setItem('authToken', authToken);
        localStorage.setItem('refreshToken', refreshToken);
        
        await getCurrentUser();
        showToast('Login successful!', 'success');
        showDashboard();
        
    } catch (error) {
        console.error('Complete error object:', error);
        console.error('Error message:', error.message);
        showToast('Login failed. Please check your credentials.', 'error');
    }
}

async function register(userData) {
    try {
        await apiCall(API_ENDPOINTS.auth.register, {
            method: 'POST',
            body: JSON.stringify(userData)
        });
        
        showToast('Registration successful! Please log in.', 'success');
        showLoginForm();
    } catch (error) {
        showToast('Registration failed. Please try again.', 'error');
    }
}

async function logout() {
    try {
        if (authToken) {
            await apiCall(API_ENDPOINTS.auth.logout, { method: 'POST' });
        }
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        authToken = null;
        refreshToken = null;
        currentUser = null;
        
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
        
        showAuthModal();
        showToast('Logged out successfully', 'info');
    }
}

async function getCurrentUser() {
    // try {
    //     currentUser = await apiCall(API_ENDPOINTS.auth.me);
    //     updateUserInfo();
    try {
        const data = await apiCall(API_ENDPOINTS.auth.me);
        currentUser = data.user || data; // Adjust based on your API response structure
        // --- ADD THIS LINE ---
        updateUserInfo(); // This will update the UI with the user's name
        return currentUser;
    } catch (error) {
        console.error('Failed to get current user:', error);
        logout();
    }
}

// UI Functions
function showLoading() {
    const loading = $('#loading');
    if (loading) loading.classList.add('show');
}

function hideLoading() {
    const loading = $('#loading');
    if (loading) loading.classList.remove('show');
}

function showToast(message, type = 'info') {
    const toastContainer = $('#toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    }[type];
    
    toast.innerHTML = `
        <i class="${icon}"></i>
        <span>${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showAuthModal() {
    const authModal = $('#auth-modal');
    const dashboard = $('#dashboard');

    if (authModal) authModal.classList.add('show'); // Change here
    if (dashboard) dashboard.style.display = 'none'; // Keep this if dashboard is hidden when modal is shown
}

function hideAuthModal() {
    const authModal = $('#auth-modal');
    if (authModal) authModal.classList.remove('show'); // Change here
}

function showDashboard() {
    hideAuthModal();
    const dashboard = $('#dashboard');
    if (dashboard) dashboard.style.display = 'block';
    loadDashboardData();
}

function showLoginForm() {
    const loginForm = $('#login-form');
    const registerForm = $('#register-form');
    const authTitle = $('#auth-title');
    
    if (loginForm) loginForm.style.display = 'block';
    if (registerForm) registerForm.style.display = 'none';
    if (authTitle) authTitle.textContent = 'Welcome Back';
}

function showRegisterForm() {
    const loginForm = $('#login-form');
    const registerForm = $('#register-form');
    const authTitle = $('#auth-title');
    
    if (loginForm) loginForm.style.display = 'none';
    if (registerForm) registerForm.style.display = 'block';
    if (authTitle) authTitle.textContent = 'Create Account';
}

function updateUserInfo() {
    if (currentUser) {
        const userName = $('#user-name');
        if (userName) userName.textContent = currentUser.username || currentUser.full_name;
    }
}

function switchSection(sectionName) {
    // Hide all sections
    $$('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from all nav links
    $$('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Show selected section
    const section = $(`#${sectionName}-section`);
    if (section) section.classList.add('active');
    
    // Add active class to selected nav link
    const navLink = $(`.nav-link[data-section="${sectionName}"]`);
    if (navLink) navLink.classList.add('active');
    
    currentSection = sectionName;
    
    // Load section data
    loadSectionData(sectionName);
}

async function loadSectionData(sectionName) {
    switch (sectionName) {
        case 'overview':
            await loadOverviewData();
            break;
        case 'tasks':
            await loadTasks();
            break;
        case 'categories':
            await loadCategories();
            break;
        case 'achievements':
            await loadAchievements();
            break;
        case 'weekly-reviews':
            await loadWeeklyReviews();
            break;
        case 'profile':
            await loadProfile();
            break;
    }
}

async function loadDashboardData() {
    await loadOverviewData();
    await loadCategories(); // Load categories for task form
}

async function loadOverviewData() {
    try {
        if (!currentUser || !currentUser.id) {
            console.error('No current user or user ID');
            return;
        }
        
        // Load XP and level data - No user ID needed, API uses logged-in user
        const levelUrl = `${API_ENDPOINTS.xp}level/`;

        const xpData = await apiCall(levelUrl);
        updateXPDisplay(xpData);
        
        // Load task stats
        const taskStats = await apiCall(`${API_ENDPOINTS.tasks}stats/`);
        updateTaskStats(taskStats);
        
        // Load recent tasks
        const tasks = await apiCall(`${API_ENDPOINTS.tasks}?limit=5`);
        displayRecentTasks(tasks.results || tasks);
        
        // Load achievements count
        const achievements = await apiCall(`${API_ENDPOINTS.achievements}unlocked/`);
        const unlockedAchievements = $('#unlocked-achievements');
        if (unlockedAchievements) unlockedAchievements.textContent = achievements.length || 0;
        
    } catch (error) {
        console.error('Failed to load overview data:', error);
    }
}


function updateXPDisplay(xpData) {
    const currentXP = xpData.total_xp || 0;
    const currentLevel = xpData.current_level || 1;
    const xpProgressInLevel = xpData.xp_progress_in_level || 0;
    const xpNeededForNext = xpData.xp_needed_for_next_level || 0;
    const xpForNextLevel = xpData.xp_for_next_level || 0;

    // Update total XP displays
    const currentXPElements = $$('.current-xp');
    currentXPElements.forEach(el => el.textContent = `${currentXP} XP`);
    
    // Update level displays
    const currentLevelEl = $('#current-level');
    const userLevelEl = $('#user-level');
    
    if (currentLevelEl) currentLevelEl.textContent = currentLevel;
    if (userLevelEl) userLevelEl.textContent = currentLevel;
    
    // Update progress bar
    const progressPercentage = xpData.progress_percentage || 0;
    const xpProgressFill = $('#xp-progress-fill');
    const xpProgressText = $('#xp-progress-text');
    
    if (xpProgressFill) xpProgressFill.style.width = `${progressPercentage}%`;
    
    if (xpProgressText) {
        // Show progress within current level segment
        const xpRequiredForLevelSegment = xpForNextLevel - (xpData.xp_for_current_level || 0);
        xpProgressText.textContent = `${xpProgressInLevel}/${xpRequiredForLevelSegment} XP`;
    }
    
    // Update streaks
    const currentStreakEl = $('#current-streak');
    const longestStreakEl = $('#longest-streak');
    
    if (currentStreakEl) currentStreakEl.textContent = xpData.current_streak || 0;
    if (longestStreakEl) longestStreakEl.textContent = xpData.longest_streak || 0;
}

function updateTaskStats(stats) {
    const totalTasksEl = $('#total-tasks');
    const completedTasksEl = $('#completed-tasks');
    const pendingTasksEl = $('#pending-tasks');
    
    if (totalTasksEl) totalTasksEl.textContent = stats.total_tasks || 0;
    if (completedTasksEl) completedTasksEl.textContent = stats.completed_tasks || 0;
    if (pendingTasksEl) pendingTasksEl.textContent = (stats.total_tasks || 0) - (stats.completed_tasks || 0);
}

function displayRecentTasks(tasks) {
    const container = $('#recent-tasks-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p class="text-center">No recent tasks found.</p>';
        return;
    }
    
    tasks.forEach(task => {
        const taskElement = createTaskElement(task);
        container.appendChild(taskElement);
    });
}

// async function loadTasks() {
//     try {
//         const tasks = await apiCall(API_ENDPOINTS.tasks);
//         displayTasks(tasks.results || tasks);
//     } catch (error) {
//         console.error('Failed to load tasks:', error);
//     }
// }
// Update the loadTasks function
async function loadTasks() {
    try {
        // Build query parameters based on current filters
        const params = new URLSearchParams();
        if (currentCategoryFilter !== 'all') params.append('category', currentCategoryFilter);
        if (currentStatusFilter !== 'all') params.append('is_completed', currentStatusFilter === 'completed');
        if (currentPriorityFilter !== 'all') params.append('priority', currentPriorityFilter);
        
        // Add query string to endpoint
        const queryString = params.toString();
        const endpoint = queryString 
            ? `${API_ENDPOINTS.tasks}?${queryString}`
            : API_ENDPOINTS.tasks;
        
        const tasks = await apiCall(endpoint);
        displayTasks(tasks.results || tasks);
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

function displayTasks(tasks) {
    const container = $('#tasks-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p class="text-center">No tasks found. Create your first task!</p>';
        return;
    }
    
    tasks.forEach(task => {
        const taskElement = createTaskElement(task, true);
        container.appendChild(taskElement);
    });
}

function createTaskElement(task, showActions = false) {
    const taskDiv = document.createElement('div');
    taskDiv.className = `task-item ${task.is_completed ? 'completed' : ''}`;

    const priorityClass = task.priority ? task.priority.toLowerCase() : 'medium';
    const categoryColor = task.category_color || '#667eea';

    // Check if task can be completed
    const canComplete = !task.timing_info || task.timing_info.can_complete !== false;
    const timingMessage = task.timing_info ? task.timing_info.message : '';

    // Determine if task can be deleted
    const canDelete = !task.is_completed; // Only allow deletion if not completed
    const canEdit = !task.is_completed;


    taskDiv.innerHTML = `
        <div class="task-info">
            <h4 class="task-title ${task.is_completed ? 'completed' : ''}">${task.title}</h4>
            <div class="task-meta">
                <span class="task-category" style="background-color: ${categoryColor}">
                    ${task.category_name || 'No Category'}
                </span>
                <span class="task-priority ${priorityClass}">${task.priority || 'Medium'}</span>
                ${task.xp_value ? `<span class="task-xp">${task.xp_value} XP</span>` : ''}
            </div>
            ${task.description ? `<p class="task-description">${task.description}</p>` : ''}
            ${task.due_date ? `<p class="task-due-date"><i class="fas fa-clock"></i> Due: ${formatDate(task.due_date)}</p>` : ''}
            ${timingMessage ? `<p class="task-timing-info"><i class="fas fa-info-circle"></i> ${timingMessage}</p>` : ''}
        </div>
        ${showActions ? `
            <div class="task-actions">
                ${!task.is_completed ? `
                    <button class="btn btn-success ${!canComplete ? 'disabled' : ''}"
                            onclick="completeTask(${task.id})"
                            ${!canComplete ? 'disabled title="' + (task.timing_info?.completion_message || 'Cannot complete yet') + '"' : ''}>
                        <i class="fas fa-check"></i> Complete
                    </button>
                ` : ''}
                <button class="btn btn-secondary" ${!canEdit ? 'disabled' : ''}" 
                        onclick="editTask(${task.id})"
                        ${!canEdit ? 'disabled title="Cannot Edit a completed task"' : ''}>
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-danger ${!canDelete ? 'disabled' : ''}"
                        onclick="deleteTask(${task.id})"
                        ${!canDelete ? 'disabled title="Cannot delete a completed task"' : ''}>
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        ` : ''}
    `;

    return taskDiv;
}

async function completeTask(taskId) {
    try {
        // ✅ GET full task first to supply required fields
        const task = await apiCall(`${API_ENDPOINTS.tasks}${taskId}/`);

        // ✅ PATCH with required data
        await apiCall(`${API_ENDPOINTS.tasks}${taskId}/complete/`, {
            method: 'PATCH',
            body: JSON.stringify({
                title: task.title,
                category: task.category,
                is_completed: true
            })
        });

        showToast('Task completed successfully!', 'success');
        await loadSectionData(currentSection);
    } catch (error) {
        console.error('Failed to complete task:', error);
        showToast('Failed to complete task', 'error');
    }
}

// Alternative version if you want to handle the timing restriction differently
async function completeTaskWithTimingCheck(taskId) {
    try {
        const response = await apiCall(`${API_ENDPOINTS.tasks}${taskId}/complete/`, {
            method: 'PATCH'
        });
        
        // Check the timing info from the response
        if (response.task && response.task.timing_info) {
            const timingInfo = response.task.timing_info;
            
            if (!timingInfo.can_complete) {
                showToast(timingInfo.completion_message || 'Task cannot be completed yet', 'warning');
                return;
            }
        }
        
        // Check if XP was earned
        if (response.xp_earned && Array.isArray(response.xp_earned)) {
            const [xpEarned, message] = response.xp_earned;
            
            if (xpEarned) {
                const xpAmount = response.task.xp_value || 0;
                showToast(`Task completed! You earned ${xpAmount} XP!`, 'success');
            } else {
                showToast(message || 'Task completed but no XP earned', 'info');
            }
        } else {
            showToast('Task completed successfully!', 'success');
        }
        
        // Refresh data
        await loadSectionData(currentSection);
        
        if (currentSection !== 'tasks') {
            await loadOverviewData();
        }
        
    } catch (error) {
        console.error('Failed to complete task:', error);
        showToast('Failed to complete task', 'error');
    }
}

// Enhanced version that shows more detailed information
async function completeTaskDetailed(taskId) {
    try {
        const response = await apiCall(`${API_ENDPOINTS.tasks}${taskId}/complete/`, {
            method: 'PATCH'
        });
        
  
        
        // Handle timing restrictions
        if (response.task && response.task.timing_info && !response.task.timing_info.can_complete) {
            showToast(response.task.timing_info.completion_message, 'warning');
            return;
        }
        
        // Check completion status and XP
        if (response.xp_earned && Array.isArray(response.xp_earned)) {
            const [xpEarned, message] = response.xp_earned;
            
            if (xpEarned) {
                const xpAmount = response.task.xp_value || 0;
                const totalXp = response.total_xp || 0;
                const level = response.current_level || 1;
                
                showToast(`🎉 Task completed! +${xpAmount} XP (Total: ${totalXp} XP, Level ${level})`, 'success');
            } else {
                showToast(`⚠️ ${message}`, 'warning');
                return; // Don't refresh if task wasn't actually completed
            }
        } else if (response.message) {
            showToast(response.message, 'success');
        } else {
            showToast('Task completed!', 'success');
        }
        
        // Refresh the UI
        await loadSectionData(currentSection);
        
        if (currentSection !== 'tasks') {
            await loadOverviewData();
        }
        
    } catch (error) {
        console.error('Failed to complete task:', error);
        showToast('Failed to complete task', 'error');
    }
}

async function deleteTask(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }
    
    try {
        await apiCall(`${API_ENDPOINTS.tasks}${taskId}/`, {
            method: 'DELETE'
        });
        
        showToast('Task deleted successfully', 'success');
        await loadSectionData(currentSection);
    } catch (error) {
        showToast('Failed to delete task', 'error');
    }
}

async function loadCategories() {
    try {
        const categories = await apiCall(API_ENDPOINTS.categories);
        displayCategories(categories.results || categories);
        updateCategorySelects(categories.results || categories);
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

function displayCategories(categories) {
    const container = $('#categories-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!categories || categories.length === 0) {
        container.innerHTML = '<p class="text-center">No categories found. Create your first category!</p>';
        return;
    }
    
    categories.forEach(category => {
        const categoryElement = createCategoryElement(category);
        container.appendChild(categoryElement);
    });
}

function createCategoryElement(category) {
    const categoryDiv = document.createElement('div');
    categoryDiv.className = 'category-card';
    
    categoryDiv.innerHTML = `
        <div class="category-header">
            <h4 class="category-name">${category.name}</h4>
            <div class="category-color" style="background-color: ${category.color}"></div>
        </div>
        <p class="category-description">${category.description || 'No description'}</p>
        <div class="category-stats">
            <span class="category-task-count">${category.task_count || 0} tasks</span>
            <span class="category-xp-multiplier">${category.xp_multiplier}x XP</span>
        </div>
        <div class="category-actions">
            <button class="btn btn-secondary btn-sm" onclick="editCategory(${category.id})">
                <i class="fas fa-edit"></i> Edit
            </button>
            <button class="btn btn-danger btn-sm" onclick="deleteCategory(${category.id})">
                <i class="fas fa-trash"></i> Delete
            </button>
        </div>
    `;
    
    return categoryDiv;
}

function updateCategorySelects(categories) {
    const categorySelects = ['#task-category', '#category-filter'];
    
    categorySelects.forEach(selector => {
        const select = $(selector);
        if (!select) return;
        
        // Clear existing options (except the first one)
        const firstOption = select.firstElementChild;
        select.innerHTML = '';
        if (firstOption) select.appendChild(firstOption);
        
        // Add category options
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            select.appendChild(option);
        });
    });
}
async function loadAchievements() {
    try {
        const allResponse = await apiCall(`${API_ENDPOINTS.achievements}`);
        
        // Extract the results array from paginated response
        const all = allResponse.results || [];
        
        displayAchievements(all);
    } catch (error) {
        console.error('Failed to load achievements:', error);
    }
}

function displayAchievements(achievements) {
    const container = document.getElementById('achievements-list');
    
    if (!container) {
        console.error('achievements-list container not found');
        return;
    }
    
    container.innerHTML = '';
    
    // Sort achievements: unlocked first, then by type or name
    const sortedAchievements = achievements.sort((a, b) => {
        if (a.is_unlocked && !b.is_unlocked) return -1;
        if (!a.is_unlocked && b.is_unlocked) return 1;
        return a.name.localeCompare(b.name);
    });
    
    sortedAchievements.forEach(achievement => {
        const achievementElement = createAchievementElement(achievement, achievement.is_unlocked);
        container.appendChild(achievementElement);
    });
    
    // Add summary info
    const unlockedCount = achievements.filter(a => a.is_unlocked).length;
    const totalCount = achievements.length;
    
    // You could add this info to the section header
    const sectionHeader = document.querySelector('#achievements-section .section-header h2');
    if (sectionHeader) {
        sectionHeader.textContent = `Achievements (${unlockedCount}/${totalCount})`;
    }
}

function createAchievementElement(achievement, isUnlocked) {
    const achievementDiv = document.createElement('div');
    achievementDiv.className = `achievement-card ${isUnlocked ? 'unlocked' : 'locked'}`;
    
    achievementDiv.innerHTML = `
        <div class="achievement-icon">
            <span class="achievement-emoji">${achievement.icon || '🏆'}</span>
        </div>
        <div class="achievement-info">
            <h4 class="achievement-name">${achievement.name}</h4>
            <p class="achievement-description">${achievement.description}</p>
            <div class="achievement-meta">
                <span class="achievement-xp">${achievement.xp_reward} XP</span>
                <span class="achievement-type">${achievement.achievement_type_display}</span>
                ${isUnlocked ? 
                    `<span class="achievement-date">✅ Unlocked</span>` : 
                    `<span class="achievement-progress">Progress: ${achievement.progress}/${achievement.threshold}</span>`
                }
            </div>
            ${!isUnlocked && achievement.progress > 0 ? `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${Math.min((achievement.progress / achievement.threshold) * 100, 100)}%"></div>
                </div>
            ` : ''}
        </div>
    `;
    
    return achievementDiv;
}

// Helper function for date formatting
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}
async function loadWeeklyReviews() {
    try {
        const reviews = await apiCall(API_ENDPOINTS.weeklyReviews);
        displayWeeklyReviews(reviews.results || reviews);
    } catch (error) {
        console.error('Failed to load weekly reviews:', error);
    }
}

function displayWeeklyReviews(reviews) {
    const container = $('#weekly-reviews-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!reviews || reviews.length === 0) {
        container.innerHTML = '<p class="text-center">No weekly reviews found.</p>';
        return;
    }
    
    reviews.forEach(review => {
        const reviewElement = createWeeklyReviewElement(review);
        container.appendChild(reviewElement);
    });
}

function createWeeklyReviewElement(review) {
    const reviewDiv = document.createElement('div');
    reviewDiv.className = 'weekly-review-card';
    
    reviewDiv.innerHTML = `
        <div class="review-header">
            <h4 class="review-title">Week of ${formatDate(review.week_start)}</h4>
            <span class="review-score">${review.overall_score}/10</span>
        </div>
        <div class="review-content">
            <div class="review-section">
                <h5>Accomplishments</h5>
                <p>${review.accomplishments || 'No accomplishments recorded.'}</p>
            </div>
            <div class="review-section">
                <h5>Challenges</h5>
                <p>${review.challenges || 'No challenges recorded.'}</p>
            </div>
            <div class="review-section">
                <h5>Next Week Goals</h5>
                <p>${review.next_week_goals || 'No goals set.'}</p>
            </div>
        </div>
        <div class="review-stats">
            <span>Tasks Completed: ${review.tasks_completed}</span>
            <span>XP Earned: ${review.xp_earned}</span>
        </div>
    `;
    
    return reviewDiv;
}

async function loadProfile() {
    try {
        const profile = await apiCall(API_ENDPOINTS.profile);
        displayProfile(profile);
    } catch (error) {
        console.error('Failed to load profile:', error);
    }
}

function displayProfile(profile) {
    const container = $('#profile-content');
    if (!container) return;
    
    container.innerHTML = `
        <div class="profile-section">
            <h3>Profile Information</h3>
            <form id="profile-form">
                <div class="form-group">
                    <label for="profile-username">Username</label>
                    <input type="text" id="profile-username" value="${profile.username || ''}" readonly>
                </div>
                <div class="form-group">
                    <label for="profile-email">Email</label>
                    <input type="email" id="profile-email" value="${profile.email || ''}" readonly>
                </div>
                <div class="form-group">
                    <label for="profile-full-name">Full Name</label>
                    <input type="text" id="profile-full-name" value="${profile.full_name || ''}">
                </div>
                <div class="form-group">
                    <label for="profile-bio">Bio</label>
                    <textarea id="profile-bio">${profile.bio || ''}</textarea>
                </div>
                <button type="submit" class="btn btn-primary">Update Profile</button>
            </form>
        </div>
        <div class="profile-section">
            <h3>Account Statistics</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>Total XP</h4>
                    <p>${profile.total_xp || 0}</p>
                </div>
                <div class="stat-card">
                    <h4>Current Level</h4>
                    <p>${profile.current_level || 1}</p>
                </div>
                <div class="stat-card">
                    <h4>Tasks Completed</h4>
                    <p>${profile.tasks_completed || 0}</p>
                </div>
                <div class="stat-card">
                    <h4>Achievements Unlocked</h4>
                    <p>${profile.achievements_count || 0}</p>
                </div>
            </div>
        </div>
    `;
    
    // Add event listener for profile form
    const profileForm = $('#profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', updateProfile);
    }
}

// Form handling functions

function hideTaskModal() {
    const modal = document.getElementById('task-modal');
    if (modal) {
        modal.classList.remove('show'); // Change here
    }
}

async function createTask(taskData) {
    const response = await apiCall(API_ENDPOINTS.tasks, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData)
    });
    return response;
}

async function editTask(taskId) {
    try {
        // 1. Fetch the specific task data from the API
        const task = await apiCall(`${API_ENDPOINTS.tasks}${taskId}/`);

        // 2. Call showTaskModal with the complete task object.
        //    The showTaskModal function will handle populating the form.
        showTaskModal(task);
        
    } catch (error) {
        showToast('Failed to load task details', 'error');
    }
}

async function fetchTaskForEdit(taskId) {
    try {
        const taskData = await apiCall(`${API_ENDPOINTS.tasks}${taskId}/`);
        showTaskModal(taskData);
    } catch (error) {
        console.error('Failed to fetch task for editing:', error);
        showToast('Failed to load task data', 'error');
    }
}


async function updateTask(taskId, taskData) {
    const response = await apiCall(`${API_ENDPOINTS.tasks}${taskId}/`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(taskData)
    });
    return response;
}


function setupTaskModalEventListeners() {
    // Add task button
    const addTaskBtn = document.getElementById('add-task-btn');
    if (addTaskBtn) {
        addTaskBtn.addEventListener('click', () => showTaskModal());
    }

    // Task form submission
    const taskForm = document.getElementById('task-form');
    if (taskForm) {
        taskForm.addEventListener('submit', handleTaskFormSubmit);
    }

    // Modal close buttons
    const modal = document.getElementById('task-modal');
    if (modal) {
        // Close button
        const closeBtn = modal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', hideTaskModal);
        }
        
        // Click outside modal to close
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                hideTaskModal();
            }
        });
    }

    // Escape key to close modal
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modal = document.getElementById('task-modal');
            if (modal && modal.style.display === 'block') {
                hideTaskModal();
            }
        }
    });
}

// Call this when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupTaskModalEventListeners();
});


async function createCategory(formData) {
    try {
        await apiCall(API_ENDPOINTS.categories, {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showToast('Category created successfully!', 'success');
        
        // Reset form and close modal
        const categoryForm = $('#category-form');
        if (categoryForm) categoryForm.reset();
        
        const categoryModal = $('#category-modal');
        if (categoryModal) categoryModal.classList.add('show'); 
        
        // Refresh data
        await loadCategories();
    } catch (error) {
        showToast('Failed to create category', 'error');
    }
}

async function editCategory(categoryId) {
    try {
        const category = await apiCall(`${API_ENDPOINTS.categories}${categoryId}/`);
        populateCategoryForm(category);
        showCategoryModal(true, categoryId);
    } catch (error) {
        showToast('Failed to load category details', 'error');
    }
}

async function deleteCategory(categoryId) {
    if (!confirm('Are you sure you want to delete this category? This action cannot be undone.')) {
        return;
    }
    
    try {
        await apiCall(`${API_ENDPOINTS.categories}${categoryId}/`, {
            method: 'DELETE'
        });
        
        showToast('Category deleted successfully', 'success');
        await loadCategories();
    } catch (error) {
        showToast('Failed to delete category', 'error');
    }
}

async function updateProfile(event) {
    event.preventDefault();
    
    const formData = {
        full_name: $('#profile-full-name').value,
        bio: $('#profile-bio').value
    };
    
    try {
        await apiCall(API_ENDPOINTS.profile, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
        
        showToast('Profile updated successfully!', 'success');
        await getCurrentUser();
    } catch (error) {
        showToast('Failed to update profile', 'error');
    }
}

async function handleTaskFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const taskId = form.getAttribute('data-task-id');
    const isEditing = !!taskId;
    
    // Get form data
    const formData = new FormData(form);
    const taskData = {
        title: formData.get('title') || document.getElementById('task-title').value,
        description: formData.get('description') || document.getElementById('task-description').value,
        category: formData.get('category') || document.getElementById('task-category').value,
        difficulty: formData.get('difficulty') || document.getElementById('task-difficulty').value,
        priority: formData.get('priority') || document.getElementById('task-priority').value,
        due_date: formData.get('due_date') || document.getElementById('task-due-date').value
    };
    
    // Validate required fields
    if (!taskData.title.trim()) {
        showToast('Please enter a task title', 'error');
        return;
    }
    
    if (!taskData.category) {
        showToast('Please select a category', 'error');
        return;
    }
    
    try {
        if (isEditing) {
            const updatedTask = await updateTask(taskId, taskData);
            // Find the specific task element and replace its content
            const taskElement = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
            if (taskElement) {
            const newTaskElement = createTaskElement(updatedTask); // Create updated HTML
            taskElement.parentNode.replaceChild(newTaskElement, taskElement);
            }
            showToast('Task updated successfully!', 'success');
        } else {
            const newTask = await createTask(taskData);
            showToast('Task created successfully!', 'success');
            // Instead of reloading, just add the new task to the top of the list
            const container = $('#tasks-list');
            const taskElement = createTaskElement(newTask, true);
            container.prepend(taskElement); // Use prepend to add it to the top
        }

        hideTaskModal();
        // Refresh overview data, which is lighter
        await loadOverviewData();
        
        // Refresh overview data if not currently in tasks section
        if (currentSection !== 'tasks') {
            await loadOverviewData();
        }
        
    } catch (error) {
        console.error('Failed to save task:', error);
        showToast(`Failed to ${isEditing ? 'update' : 'create'} task: ${error.message}`, 'error');
    }
}

function showTaskModal(taskData = null) {
    const modal = document.getElementById('task-modal');
    const title = document.getElementById('task-modal-title');
    const form = document.getElementById('task-form');

    if (!modal || !form) {
        console.error('Task modal or form not found');
        return;
    }

    // Reset form
    form.reset();

    if (taskData) {
        // Editing existing task
        title.textContent = 'Edit Task';
        populateTaskForm(taskData);
        form.setAttribute('data-task-id', taskData.id);
    } else {
        // Adding new task
        title.textContent = 'Add New Task';
        form.removeAttribute('data-task-id');
    }

    modal.classList.add('show');

    // Focus on first input
    const firstInput = form.querySelector('input, select, textarea');
    if (firstInput) firstInput.focus();
}


const categoryModal = $('#category-modal');
const categoryModalTitle = $('#category-modal-title');
const categoryForm = $('#category-form');
const categoryNameInput = $('#category-name');
const categoryDescriptionInput = $('#category-description');
const categoryColorInput = $('#category-color');
const categoryMultiplierInput = $('#category-multiplier');
let currentCategoryId = null; // To store the ID of the category being edited

function showCategoryModal(isEditMode = false, categoryId = null) {
    if (!categoryModal) {
        console.error('Category modal not found!');
        return;
    }
    categoryModal.classList.add('show');
    // Only reset form if NOT in edit mode
    if (!isEditMode && categoryForm) {
        categoryForm.reset();
    }

    if (isEditMode && categoryId) {
        categoryModalTitle.textContent = 'Edit Category';
        categoryForm.setAttribute('data-category-id', categoryId);
        currentCategoryId = categoryId;
    } else {
        categoryModalTitle.textContent = 'Add New Category';
        categoryForm.removeAttribute('data-category-id');
        currentCategoryId = null;
        categoryColorInput.value = '#007bff'; // Default color
        categoryMultiplierInput.value = '1.0'; // Default multiplier
    }
}

function hideCategoryModal() {
    if (categoryModal) {
        categoryModal.classList.remove('show');
    }
}

function populateCategoryForm(category) {
    if (category) {
        categoryNameInput.value = category.name || '';
        categoryDescriptionInput.value = category.description || '';
        categoryColorInput.value = category.color || '#007bff';
        categoryMultiplierInput.value = category.xp_multiplier || '1.0';
    }
}

async function handleCategoryFormSubmit(event) {
    event.preventDefault();

    const formData = {
        name: categoryNameInput.value,
        description: categoryDescriptionInput.value,
        color: categoryColorInput.value,
        xp_multiplier: parseFloat(categoryMultiplierInput.value)
    };

    const isEditing = categoryForm.hasAttribute('data-category-id');
    const categoryId = categoryForm.getAttribute('data-category-id');

    try {
        if (isEditing) {
            await apiCall(`${API_ENDPOINTS.categories}${categoryId}/`, {
                method: 'PUT',
                body: JSON.stringify(formData)
            });
            showToast('Category updated successfully!', 'success');
        } else {
            await apiCall(API_ENDPOINTS.categories, {
                method: 'POST',
                body: JSON.stringify(formData)
            });
            showToast('Category created successfully!', 'success');
        }
        hideCategoryModal();
        await loadCategories(); // Refresh categories list
    } catch (error) {
        showToast(`Failed to ${isEditing ? 'update' : 'create'} category`, 'error');
    }
}

function setupCategoryModalEventListeners() {
    // Add category button
    const addCategoryBtn = $('#add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', () => showCategoryModal(false));
    }

    // Category form submission
    if (categoryForm) {
        categoryForm.addEventListener('submit', handleCategoryFormSubmit);
    }

    // Close button inside modal
    if (categoryModal) {
        const closeBtn = categoryModal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', hideCategoryModal);
        }
        // Click outside modal to close
        categoryModal.addEventListener('click', (event) => {
            if (event.target === categoryModal) {
                hideCategoryModal();
            }
        });
    }

    // Escape key to close modal
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (categoryModal && categoryModal.style.display === 'flex') {
                hideCategoryModal();
            }
        }
    });
}

// Call this when the DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupTaskModalEventListeners(); // Existing
    setupCategoryModalEventListeners(); // New
});

function populateTaskForm(taskData) {
    document.getElementById('task-title').value = taskData.title || '';
    document.getElementById('task-description').value = taskData.description || '';
    document.getElementById('task-category').value = taskData.category || '';
    document.getElementById('task-difficulty').value = taskData.difficulty || 'medium';
    document.getElementById('task-priority').value = taskData.priority || 'medium';
    
    // Handle due date format
    if (taskData.due_date) {
        const date = new Date(taskData.due_date);
        const localDateTime = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
            .toISOString().slice(0, 16);
        document.getElementById('task-due-date').value = localDateTime;
    }
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
// Add this helper function
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

// Event listeners setup
function setupEventListeners() {
    // Auth form submissions
    const loginForm = $('#login-form');
    if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const emailInput = $('#login-email');
        const passwordInput = $('#login-password');
        
        if (!emailInput || !passwordInput) {
            showToast('Form elements not found', 'error');
            return;
        }
        
        const email = emailInput.value;
        const password = passwordInput.value;
        await login(email, password);
    });
}

    const registerForm = $('#register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userData = {
                username: $('#reg-username').value, // Was register-username
                email: $('#reg-email').value,       // Was register-email
                password: $('#reg-password').value, // Was register-password
                full_name: $('#reg-first-name').value + ' ' + $('#reg-last-name').value
            };
            await register(userData);
    });
}


    // Add Category button
    const addCategoryBtn = $('#add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', () => {
            showCategoryModal(false); 
        });
    }
    // Category form submission
    const categoryForm = $('#category-form');
    if (categoryForm) {
        categoryForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                name: $('#category-name').value,
                description: $('#category-description').value,
                color: $('#category-color').value,
                xp_multiplier: parseFloat($('#category-xp-multiplier').value) || 1
            };

            const categoryModal = $('#category-modal');
            const isEdit = categoryModal.dataset.isEdit === 'true';
            const categoryId = categoryModal.dataset.categoryId;

            if (isEdit && categoryId) {
                await updateCategory(categoryId, formData);
            } else {
                await createCategory(formData);
            }
        });
    }

    // ✅ FIXED: Navigation links - use $$ instead of $
    $$('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            if (section) {
                switchSection(section);
            }
        });
    });

    // ✅ FIXED: Modal close buttons
    $$('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = btn.closest('.modal');
            if (modal) {
                modal.classList.remove('show');
            }
        });
    });

    // ✅ FIXED: Modal backdrop clicks
    $$('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        });
    });

    // Auth toggle buttons
    const showRegisterBtn = $('#show-register');
    const showLoginBtn = $('#show-login');

    if (showRegisterBtn) {
        showRegisterBtn.addEventListener('click', showRegisterForm);
    }
    if (showLoginBtn) {
        showLoginBtn.addEventListener('click', showLoginForm);
    }

    // Logout button
    const logoutBtn = $('#logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }

    // Category filter
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', (event) => {
            currentCategoryFilter = event.target.value;
            loadTasks();
        });
    }

    // Status filter
    const statusFilter = document.getElementById('status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (event) => {
            currentStatusFilter = event.target.value;
            loadTasks();
        });
    }

    // Priority filter (keep your existing implementation)
    const priorityFilter = document.getElementById('priority-filter');
    if (priorityFilter) {
        priorityFilter.addEventListener('change', (event) => {
            currentPriorityFilter = event.target.value;
            loadTasks();
        });
    }


    const createCategoryBtn = $('#create-category-btn');
    if (createCategoryBtn) {
        createCategoryBtn.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = {
                name: $('#category-name').value,
                description: $('#category-description').value,
                color: $('#category-color').value,
                xp_multiplier: parseFloat($('#category-xp-multiplier').value) || 1
            };

            const categoryModal = $('#category-modal');
            const isEdit = categoryModal.dataset.isEdit === 'true';
            const categoryId = categoryModal.dataset.categoryId;

            if (isEdit && categoryId) {
                await updateCategory(categoryId, formData);
            } else {
                await createCategory(formData);
            }
        });
    }

    // Task filters
    const taskFilters = ['#priority-filter', '#category-filter', '#status-filter'];
    taskFilters.forEach(selector => {
        const filter = $(selector);
        if (filter) {
            filter.addEventListener('change', filterTasks);
        }
    });

    // Search functionality
    const taskSearch = $('#task-search');
    if (taskSearch) {
        taskSearch.addEventListener('input', debounce(searchTasks, 300));
    }
}

// Filter and search functions
function filterTasks() {
    const priorityFilter = $('#priority-filter').value;
    const categoryFilter = $('#category-filter').value;
    const statusFilter = $('#status-filter').value;
    
    const params = new URLSearchParams();
    if (priorityFilter) params.append('priority', priorityFilter);
    if (categoryFilter) params.append('category', categoryFilter);

    
    if (statusFilter) params.append('is_completed', statusFilter);
    
    loadFilteredTasks(params.toString());
}

function searchTasks() {
    const searchTerm = $('#task-search').value;
    const params = new URLSearchParams();
    if (searchTerm) params.append('search', searchTerm);
    
    loadFilteredTasks(params.toString());
}

async function loadFilteredTasks(queryString) {
    try {
        const endpoint = queryString ? `${API_ENDPOINTS.tasks}?${queryString}` : API_ENDPOINTS.tasks;
        const tasks = await apiCall(endpoint);
        displayTasks(tasks.results);
    } catch (error) {
        console.error('Failed to load filtered tasks:', error);
    }
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Category update function
async function updateCategory(categoryId, formData) {
    try {
        await apiCall(`${API_ENDPOINTS.categories}${categoryId}/`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
        
        showToast('Category updated successfully!', 'success');
        
        // Close modal and refresh data
        const categoryModal = $('#category-modal');
        if (categoryModal) categoryModal.classList.add('show'); 
        
        await loadCategories();
    } catch (error) {
        showToast('Failed to update category', 'error');
    }
}

// Weekly review functions
async function createWeeklyReview(formData) {
    try {
        await apiCall(API_ENDPOINTS.weeklyReviews, {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showToast('Weekly review created successfully!', 'success');
        
        // Reset form and close modal
        const reviewForm = $('#weekly-review-form');
        if (reviewForm) reviewForm.reset();
        
        const reviewModal = $('#weekly-review-modal');
        if (reviewModal) reviewModal.style.display = 'none';
        
        // Refresh data
        await loadWeeklyReviews();
    } catch (error) {
        showToast('Failed to create weekly review', 'error');
    }
}

// Statistics functions
async function loadStats() {
    try {
        const stats = await apiCall(API_ENDPOINTS.stats);
        displayStats(stats);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function displayStats(stats) {
    // This would be implemented based on your specific stats requirements
    // console.log('Stats loaded:', stats);
}

// Theme functions
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.classList.contains('dark-theme') ? 'dark' : 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    body.classList.toggle('dark-theme');
    localStorage.setItem('theme', newTheme);
    
    // Update theme toggle button
    const themeToggle = $('#theme-toggle');
    if (themeToggle) {
        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }
    }
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        const themeToggle = $('#theme-toggle');
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-sun';
            }
        }
    }
}

// Notification functions
// async function checkNotifications() {
//     try {
//         const notifications = await apiCall('/notifications/');
//         displayNotifications(notifications);
//     } catch (error) {
//         console.error('Failed to load notifications:', error);
//     }
// }

// function displayNotifications(notifications) {
//     const notificationBadge = $('#notification-badge');
//     const notificationList = $('#notification-list');
    
//     if (notificationBadge) {
//         notificationBadge.textContent = notifications.length;
//         notificationBadge.style.display = notifications.length > 0 ? 'block' : 'none';
//     }
    
//     if (notificationList) {
//         notificationList.innerHTML = '';
//         notifications.forEach(notification => {
//             const notificationElement = createNotificationElement(notification);
//             notificationList.appendChild(notificationElement);
//         });
//     }
// }

function createNotificationElement(notification) {
    const notificationDiv = document.createElement('div');
    notificationDiv.className = `notification-item ${notification.is_read ? 'read' : 'unread'}`;
    
    notificationDiv.innerHTML = `
        <div class="notification-content">
            <h5 class="notification-title">${notification.title}</h5>
            <p class="notification-message">${notification.message}</p>
            <span class="notification-time">${formatDateTime(notification.created_at)}</span>
        </div>
        <div class="notification-actions">
            ${!notification.is_read ? `
                <button class="btn btn-sm btn-primary" onclick="markNotificationRead(${notification.id})">
                    Mark as Read
                </button>
            ` : ''}
            <button class="btn btn-sm btn-danger" onclick="deleteNotification(${notification.id})">
                Delete
            </button>
        </div>
    `;
    
    return notificationDiv;
}

// async function markNotificationRead(notificationId) {
//     try {
//         await apiCall(`/notifications/${notificationId}/read/`, {
//             method: 'PATCH'
//         });
        
//         await checkNotifications();
//     } catch (error) {
//         showToast('Failed to mark notification as read', 'error');
//     }
// }

// async function deleteNotification(notificationId) {
//     try {
//         await apiCall(`/notifications/${notificationId}/`, {
//             method: 'DELETE'
//         });
        
//         await checkNotifications();
//     } catch (error) {
//         showToast('Failed to delete notification', 'error');
//     }
// }

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + N: New task
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const createTaskBtn = $('#create-task-btn');
            if (createTaskBtn) createTaskBtn.click();
        }
        
        // Ctrl/Cmd + /: Search
        if ((e.ctrlKey || e.metaKey) && e.key === '/') {
            e.preventDefault();
            const taskSearch = $('#task-search');
            if (taskSearch) taskSearch.focus();
        }
        
        // Escape: Close modals
        if (e.key === 'Escape') {
           const openModal = document.querySelector('.modal.show'); // Find any open modal
            if (openModal) {
            // Add specific condition for auth-modal if needed
                if (openModal.id === 'auth-modal') {
                    return;
                }
                openModal.classList.remove('show');
            }
        }
    });
}

// // Service Worker registration (for PWA functionality)
// async function registerServiceWorker() {
//      if ('serviceWorker' in navigator) {
//         navigator.serviceWorker.register('/sw.js')
//             .then(reg => console.log('Service Worker registered:', reg))
//             .catch(err => console.error('Service Worker registration failed:', err));
//     }
// }

// Initialize application
async function initializeApp() {
    // Load theme
    loadTheme();
    
    // Setup event listeners
    setupEventListeners();
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
    
    // Check for existing auth token
    const savedToken = localStorage.getItem('authToken');
    const savedRefreshToken = localStorage.getItem('refreshToken');
    
    if (savedToken && savedRefreshToken) {
        authToken = savedToken;
        refreshToken = savedRefreshToken;
        
        try {
            await getCurrentUser();
            showDashboard();
        } catch (error) {
            console.error('Failed to restore session:', error);
            showAuthModal();
        }
    } else {
        showAuthModal();
    }
    // document.addEventListener('DOMContentLoaded', initializeApp);
    // Register service worker for PWA
    // await registerServiceWorker();
    
    // Setup periodic data refresh
    setInterval(async () => {
        if (authToken && currentUser) {
            try {
                await loadSectionData(currentSection);
                // await checkNotifications();
            } catch (error) {
                console.error('Periodic refresh failed:', error);
            }
        }
    }, 30000); // Refresh every 30 seconds
}

// Start the application when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);

// Global error handler
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    showToast('An unexpected error occurred', 'error');
});

// Handle network status changes
window.addEventListener('online', () => {
    showToast('Connection restored', 'success');
    if (currentUser) {
        loadSectionData(currentSection);
    }
});

window.addEventListener('offline', () => {
    showToast('Connection lost. Some features may not work.', 'warning');
});