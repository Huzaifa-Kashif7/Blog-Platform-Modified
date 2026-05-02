"""
Blog URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    # Basic CRUD routes - IMPORTANT: more specific routes must come first
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
path('profile/analytics/', views.analytics_dashboard, name='analytics'),
path('profile/', views.profile_detail, name='my_profile'),
path('profile/<str:username>/', views.profile_detail, name='profile_detail'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('verify-email/resend/', views.resend_verification, name='resend_verification'),
    path('post/<slug:slug>/like/', views.toggle_like, name='toggle_like'),
    path('post/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('post/<slug:slug>/bookmark/', views.toggle_bookmark, name='toggle_bookmark'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('about/', views.about_page, name='about'),
    path('', views.post_list, name='post_list'),
    path('post/create/', views.post_create, name='post_create'),  # Must come before slug pattern!
    path('post/<slug:slug>/edit/', views.post_update, name='post_update'),
    path('post/<slug:slug>/delete/', views.post_delete, name='post_delete'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),  # This must come last
    
    # AI-powered routes
    path('search/', views.semantic_search, name='semantic_search'),
    path('ai-tags/', views.ai_tags, name='ai_tags'),
    path('ai-seo/', views.ai_seo, name='ai_seo'),
]

