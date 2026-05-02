"""
Blog Views with AI-powered features
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, F
from django.core.paginator import Paginator
from django.utils import timezone
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import markdown
import json

from .models import (
    Post,
    PostLike,
    Comment,
    UserProfile,
    Category,
    Tag,
    Bookmark,
    Notification,
    PostImage,
)
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    ProfileForm,
    CommentForm,
    UserInfoForm,
)
User = get_user_model()

def create_notification(user, actor, post, notif_type, message, data=None):
    if not user or user == actor:
        return
    Notification.objects.create(
        user=user,
        actor=actor,
        post=post,
        notification_type=notif_type,
        message=message[:255],
        data=data or {}
    )


def send_verification_email(request, user):
    if not user.email:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    send_mail(
        'Verify your email address',
        f'Hi {user.get_full_name() or user.username},\n\nPlease confirm your email by visiting: {verify_url}\n\nIf you did not create an account, you can ignore this email.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )

from .ai_utils import (
    generate_embedding,
    cosine_similarity,
    generate_summary,
    generate_tags_and_category,
    generate_seo_metadata
)
from .validators import validate_image_upload
from django.core.exceptions import ValidationError as DjangoValidationError


def post_list(request):
    """Display list of all blog posts"""
    posts = (
        Post.objects.filter(status='published')
        .select_related('author', 'primary_category')
        .prefetch_related('manual_tags')
        .annotate(total_likes=Count('likes', distinct=True), total_comments=Count('comments', distinct=True))
    )
    
    # Search & filters
    query = request.GET.get('q', '').strip()
    selected_category = request.GET.get('category', '').strip()
    selected_author = request.GET.get('author', '').strip()
    selected_tag = request.GET.get('tag', '').strip()

    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query) |
            Q(summary__icontains=query) |
            Q(category__icontains=query) |
            Q(manual_tags__name__icontains=query)
        ).distinct()

    if selected_category:
        posts = posts.filter(
            Q(primary_category__slug=selected_category) |
            Q(category__iexact=selected_category)
        )

    if selected_author:
        posts = posts.filter(author__username=selected_author)

    if selected_tag:
        posts = posts.filter(
            Q(manual_tags__slug=selected_tag) |
            Q(tags__icontains=selected_tag)
        )

    posts = posts.distinct()
    
    paginator = Paginator(posts, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.order_by('name')
    authors = User.objects.filter(posts__status='published').distinct()
    tag_options = Tag.objects.order_by('name')
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'categories': categories,
        'authors': authors,
        'selected_category': selected_category,
        'selected_author': selected_author,
        'selected_tag': selected_tag,
        'tag_options': tag_options,
    }
    return render(request, 'blog/post_list.html', context)


def post_detail(request, slug):
    """Display single blog post with AI-generated summary"""
    post = get_object_or_404(
        Post.objects.select_related('author', 'primary_category').prefetch_related('comments__author', 'likes', 'manual_tags', 'gallery_images'),
        slug=slug
    )
    if post.status == 'draft' and (not request.user.is_authenticated or (request.user != post.author and not request.user.is_superuser)):
        raise Http404()
    Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
    post.refresh_from_db(fields=['view_count'])
    comments = post.comments.filter(is_active=True).select_related('author')
    comment_form = CommentForm()
    is_liked = False
    is_bookmarked = False
    if request.user.is_authenticated:
        is_liked = post.likes.filter(user=request.user).exists()
        is_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()
    share_url = request.build_absolute_uri(post.get_absolute_url())
    og_image_url = None
    if post.cover_image:
        og_image_url = request.build_absolute_uri(post.cover_image.url)

    rendered_body = mark_safe(markdown.markdown(
        post.content,
        extensions=['fenced_code', 'tables']
    ))

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked,
        'is_bookmarked': is_bookmarked,
        'share_url': share_url,
        'rendered_body': rendered_body,
        'og_image_url': og_image_url,
    }
    return render(request, 'blog/post_detail.html', context)


def signup_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.user.is_authenticated:
        return redirect(next_url or 'post_list')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            send_verification_email(request, user)
            messages.success(request, 'Welcome! Your account has been created. Please verify your email.')
            return redirect(next_url or 'post_list')
        messages.error(request, 'Please correct the highlighted errors.')
    else:
        form = UserRegistrationForm()
    return render(request, 'auth/signup.html', {'form': form, 'next': next_url})


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.user.is_authenticated:
        return redirect(next_url or 'post_list')
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful!')
            if hasattr(user, 'profile') and not user.profile.email_verified:
                messages.warning(request, 'Please verify your email to unlock all features.')
            return redirect(next_url or 'post_list')
        messages.error(request, 'Invalid credentials, please try again.')
    else:
        form = UserLoginForm()
    return render(request, 'auth/login.html', {'form': form, 'next': next_url})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


def profile_detail(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        if not request.user.is_authenticated:
            return redirect('login')
        profile_user = request.user

    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    posts = profile_user.posts.all().annotate(
        total_likes=Count('likes', distinct=True),
        total_comments=Count('comments', distinct=True),
    ).order_by('-created_at')
    paginator = Paginator(posts, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    bookmarks = []
    if request.user == profile_user:
        bookmarks = Bookmark.objects.filter(user=profile_user).select_related('post', 'post__primary_category').order_by('-created_at')[:10]

    context = {
        'profile_user': profile_user,
        'profile': profile,
        'page_obj': page_obj,
        'is_owner': request.user == profile_user,
        'bookmarks': bookmarks,
    }
    return render(request, 'profile/profile_detail.html', context)


@login_required
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        info_form = UserInfoForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if info_form.is_valid() and profile_form.is_valid():
            info_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile_detail', username=request.user.username)
        messages.error(request, 'Please correct the errors below.')
    else:
        info_form = UserInfoForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'profile/profile_edit.html', {
        'info_form': info_form,
        'profile_form': profile_form,
    })


@login_required
def notifications_list(request):
    notifications = (
        Notification.objects.filter(user=request.user)
        .select_related('actor', 'post')
        .order_by('-created_at')
    )
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'profile/notifications.html', {'notifications': notifications})


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None

    if user and default_token_generator.check_token(user, token):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=['email_verified'])
            messages.success(request, 'Email verified! You can now access all features.')
        else:
            messages.info(request, 'Email already verified.')
    else:
        messages.error(request, 'Verification link is invalid or expired.')
    return redirect('post_list')


@login_required
def resend_verification(request):
    send_verification_email(request, request.user)
    messages.info(request, 'Verification email sent. Please check your inbox.')
    return redirect('post_list')


@login_required
def analytics_dashboard(request):
    posts = Post.objects.filter(author=request.user)
    total_posts = posts.count()
    total_views = posts.aggregate(total=Sum('view_count'))['total'] or 0
    likes_received = PostLike.objects.filter(post__author=request.user).count()
    comments_received = Comment.objects.filter(post__author=request.user, is_active=True).count()
    bookmarks_received = Bookmark.objects.filter(post__author=request.user).count()
    recent_posts = posts.order_by('-created_at')[:5]
    top_posts = posts.order_by('-view_count')[:5]

    context = {
        'total_posts': total_posts,
        'total_views': total_views,
        'likes_received': likes_received,
        'comments_received': comments_received,
        'bookmarks_received': bookmarks_received,
        'recent_posts': recent_posts,
        'top_posts': top_posts,
    }
    return render(request, 'profile/analytics.html', context)


@login_required
@require_POST
def toggle_like(request, slug):
    post = get_object_or_404(Post, slug=slug)
    like, created = PostLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        create_notification(
            post.author,
            request.user,
            post,
            'like',
            f"{request.user.get_full_name() or request.user.username} liked your post"
        )
    return JsonResponse({'liked': liked, 'likes': post.like_count})


@login_required
@require_POST
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        create_notification(
            post.author,
            request.user,
            post,
            'comment',
            f"{request.user.get_full_name() or request.user.username} commented on your post"
        )
        rendered_comment = render(request, 'blog/partials/comment.html', {'comment': comment, 'post': post}).content.decode('utf-8')
        return JsonResponse({
            'success': True,
            'html': rendered_comment,
            'message': 'Comment added!',
            'comment_count': post.comment_count,
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if (
        comment.author != request.user
        and comment.post.author != request.user
        and not request.user.is_superuser
    ):
        return JsonResponse({'success': False, 'error': 'Not allowed'}, status=403)

    # Notify the comment author if someone else deleted their comment
    if comment.author != request.user:
        create_notification(
            user=comment.author,
            actor=request.user,
            post=comment.post,
            notif_type='comment_removed',
            message=f"Your comment on '{comment.post.title}' was removed by the post author."
        )

    post_id = comment.post_id
    comment.soft_delete(user=request.user)
    fresh_count = Comment.objects.filter(post_id=post_id, is_active=True).count()
    return JsonResponse({
        'success': True,
        'comment_id': comment.id,
        'comment_count': fresh_count,
    })


@login_required
@require_POST
def toggle_bookmark(request, slug):
    post = get_object_or_404(Post, slug=slug)
    bookmark, created = Bookmark.objects.get_or_create(post=post, user=request.user)
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True
        create_notification(
            post.author,
            request.user,
            post,
            'bookmark',
            f"{request.user.get_full_name() or request.user.username} bookmarked your post"
        )
    return JsonResponse({
        'bookmarked': bookmarked,
        'count': post.bookmark_count,
    })


def about_page(request):
    from django.db.models import Count
    from .models import Post, Comment, Category
    
    User = get_user_model()
    
    context = {
        'total_posts': Post.objects.filter(status='published').count(),
        'total_users': User.objects.count(),
        'total_comments': Comment.objects.filter(is_active=True).count(),
        'total_categories': Category.objects.count(),
    }
    return render(request, 'pages/about.html', context)


@login_required
def post_create(request):
    """Create new blog post with AI features"""
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        slug = request.POST.get('slug', '').strip()
        meta_description = request.POST.get('meta_description', '').strip()
        seo_title = request.POST.get('seo_title', '').strip()
        ai_category = request.POST.get('category', '').strip()
        ai_tags_input = request.POST.get('tags', '').strip()
        seo_keywords_input = request.POST.get('seo_keywords', '').strip()
        primary_category_id = request.POST.get('primary_category')
        new_category_name = request.POST.get('new_category', '').strip()
        manual_tag_ids = request.POST.getlist('manual_tags')
        new_manual_tags_input = request.POST.get('new_manual_tags', '').strip()
        cover_image = request.FILES.get('cover_image')
        gallery_files = request.FILES.getlist('gallery_images')

        # Validate uploaded images
        if cover_image:
            try:
                validate_image_upload(cover_image)
            except DjangoValidationError as e:
                messages.error(request, f"Cover image error: {', '.join(e.messages)}")
                return render(request, 'blog/post_form.html', {
                    'form_type': 'create',
                    'categories': Category.objects.order_by('name'),
                    'tag_options': Tag.objects.order_by('name'),
                    'selected_manual_tags': [],
                    'selected_primary_category': None,
                })

        for gf in gallery_files:
            try:
                validate_image_upload(gf)
            except DjangoValidationError as e:
                messages.error(request, f"Gallery image '{gf.name}' error: {', '.join(e.messages)}")
                return render(request, 'blog/post_form.html', {
                    'form_type': 'create',
                    'categories': Category.objects.order_by('name'),
                    'tag_options': Tag.objects.order_by('name'),
                    'selected_manual_tags': [],
                    'selected_primary_category': None,
                })

        status = request.POST.get('status', 'published')
        if status not in dict(Post.STATUS_CHOICES):
            status = 'published'
        
        # Validate required fields
        if not title or not title.strip():
            messages.error(request, 'Title is required.')
            context = {
                'form_type': 'create',
                'categories': Category.objects.order_by('name'),
                'tag_options': Tag.objects.order_by('name'),
                'selected_manual_tags': [],
                'selected_primary_category': None,
            }
            return render(request, 'blog/post_form.html', context)
        
        if not content or not content.strip():
            messages.error(request, 'Content is required.')
            context = {
                'form_type': 'create',
                'categories': Category.objects.order_by('name'),
                'tag_options': Tag.objects.order_by('name'),
                'selected_manual_tags': [],
                'selected_primary_category': None,
            }
            return render(request, 'blog/post_form.html', context)
        
        # Parse tags (comma-separated or JSON)
        if ai_tags_input:
            if ai_tags_input.startswith('['):
                try:
                    ai_tags = json.loads(ai_tags_input)
                except:
                    ai_tags = [t.strip() for t in ai_tags_input.split(',') if t.strip()]
            else:
                ai_tags = [t.strip() for t in ai_tags_input.split(',') if t.strip()]
        else:
            ai_tags = []
        
        # Parse SEO keywords (JSON)
        seo_keywords = []
        if seo_keywords_input:
            try:
                seo_keywords = json.loads(seo_keywords_input)
                if not isinstance(seo_keywords, list):
                    seo_keywords = []
            except:
                seo_keywords = []
        
        # Create post
        post = Post(
            title=title,
            content=content,
            author=request.user,
            slug=slug if slug else None,
            meta_description=meta_description,
            seo_title=seo_title if seo_title else title,
            category=ai_category,
            tags=ai_tags,
            seo_keywords=seo_keywords,
            status=status,
            cover_image=cover_image
        )

        # Manual taxonomy handling
        primary_category = None
        if new_category_name:
            primary_category, _ = Category.objects.get_or_create(
                slug=slugify(new_category_name),
                defaults={'name': new_category_name}
            )
        elif primary_category_id:
            primary_category = Category.objects.filter(id=primary_category_id).first()

        manual_tags = list(Tag.objects.filter(id__in=manual_tag_ids))
        if new_manual_tags_input:
            for tag_name in [t.strip() for t in new_manual_tags_input.split(',') if t.strip()]:
                tag_slug = slugify(tag_name)
                tag_obj, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={'name': tag_name})
                manual_tags.append(tag_obj)

        post.primary_category = primary_category
        
        # Generate AI features if enabled
        auto_summary = request.POST.get('auto_summary', False)
        auto_embedding = request.POST.get('auto_embedding', False)
        
        if auto_summary:
            try:
                post.summary = generate_summary(content)
            except Exception as e:
                messages.warning(request, f"Summary generation failed: {e}")
        
        if auto_embedding:
            try:
                embedding_text = f"{title} {content}"
                post.embedding = generate_embedding(embedding_text)
            except Exception as e:
                messages.warning(request, f"Embedding generation failed: {e}")
        
        post.save()

        if manual_tags:
            unique_manual_tags = list(dict.fromkeys(manual_tags))
            post.manual_tags.set(unique_manual_tags)
        else:
            post.manual_tags.clear()

        if gallery_files:
            for order, image in enumerate(gallery_files, start=post.gallery_images.count()):
                PostImage.objects.create(
                    post=post,
                    image=image,
                    display_order=order
                )
        messages.success(request, 'Post created successfully!')
        return redirect('post_detail', slug=post.slug)
    
    context = {
        'form_type': 'create',
        'categories': Category.objects.order_by('name'),
        'tag_options': Tag.objects.order_by('name'),
        'selected_manual_tags': [],
        'selected_primary_category': None,
    }
    return render(request, 'blog/post_form.html', context)


@login_required
def post_update(request, slug):
    """Update existing blog post"""
    post = get_object_or_404(Post, slug=slug)
    
    # Check ownership
    if post.author != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit this post.')
        return redirect('post_detail', slug=post.slug)
    
    if request.method == 'POST':
        post.title = request.POST.get('title')
        post.content = request.POST.get('content')
        slug_input = request.POST.get('slug', '').strip()
        if slug_input:
            post.slug = slug_input
        status = request.POST.get('status', post.status)
        if status not in dict(Post.STATUS_CHOICES):
            status = post.status
        post.status = status
        
        post.meta_description = request.POST.get('meta_description', '').strip()
        seo_title = request.POST.get('seo_title', '').strip()
        if seo_title:
            post.seo_title = seo_title
        
        post.category = request.POST.get('category', '').strip()
        tags_input = request.POST.get('tags', '').strip()
        if tags_input:
            if tags_input.startswith('['):
                try:
                    post.tags = json.loads(tags_input)
                except:
                    post.tags = [t.strip() for t in tags_input.split(',') if t.strip()]
            else:
                post.tags = [t.strip() for t in tags_input.split(',') if t.strip()]

        primary_category_id = request.POST.get('primary_category')
        new_category_name = request.POST.get('new_category', '').strip()
        manual_tag_ids = request.POST.getlist('manual_tags')
        new_manual_tags_input = request.POST.get('new_manual_tags', '').strip()

        cover_image = request.FILES.get('cover_image')
        gallery_files = request.FILES.getlist('gallery_images')

        # Validate uploaded images
        if cover_image:
            try:
                validate_image_upload(cover_image)
            except DjangoValidationError as e:
                messages.error(request, f"Cover image error: {', '.join(e.messages)}")
                return redirect('post_update', slug=post.slug)

        for gf in gallery_files:
            try:
                validate_image_upload(gf)
            except DjangoValidationError as e:
                messages.error(request, f"Gallery image '{gf.name}' error: {', '.join(e.messages)}")
                return redirect('post_update', slug=post.slug)

        remove_cover = request.POST.get('remove_cover') == 'on'
        delete_gallery_ids = request.POST.getlist('delete_gallery')

        if new_category_name:
            primary_category, _ = Category.objects.get_or_create(
                slug=slugify(new_category_name),
                defaults={'name': new_category_name}
            )
            post.primary_category = primary_category
        elif primary_category_id:
            post.primary_category = Category.objects.filter(id=primary_category_id).first()
        else:
            post.primary_category = None

        manual_tags = list(Tag.objects.filter(id__in=manual_tag_ids))
        if new_manual_tags_input:
            for tag_name in [t.strip() for t in new_manual_tags_input.split(',') if t.strip()]:
                tag_slug = slugify(tag_name)
                tag_obj, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={'name': tag_name})
                manual_tags.append(tag_obj)
        
        # Update SEO keywords
        seo_keywords_input = request.POST.get('seo_keywords', '').strip()
        if seo_keywords_input:
            try:
                post.seo_keywords = json.loads(seo_keywords_input)
                if not isinstance(post.seo_keywords, list):
                    post.seo_keywords = []
            except:
                pass
        
        # Regenerate AI features if requested
        regenerate_summary = request.POST.get('regenerate_summary', False)
        regenerate_embedding = request.POST.get('regenerate_embedding', False)
        
        if regenerate_summary:
            try:
                post.summary = generate_summary(post.content)
                messages.info(request, 'Summary regenerated!')
            except Exception as e:
                messages.warning(request, f"Summary generation failed: {e}")
        
        if regenerate_embedding:
            try:
                embedding_text = f"{post.title} {post.content}"
                post.embedding = generate_embedding(embedding_text)
                messages.info(request, 'Embedding regenerated!')
            except Exception as e:
                messages.warning(request, f"Embedding generation failed: {e}")
        
        if remove_cover and post.cover_image:
            post.cover_image.delete(save=False)
            post.cover_image = None
        elif cover_image:
            if post.cover_image:
                post.cover_image.delete(save=False)
            post.cover_image = cover_image

        post.save()

        if manual_tags:
            post.manual_tags.set(list(dict.fromkeys(manual_tags)))
        else:
            post.manual_tags.clear()

        if delete_gallery_ids:
            PostImage.objects.filter(id__in=delete_gallery_ids, post=post).delete()

        if gallery_files:
            start_order = post.gallery_images.count()
            for idx, image in enumerate(gallery_files, start=start_order):
                PostImage.objects.create(
                    post=post,
                    image=image,
                    display_order=idx
                )
        messages.success(request, 'Post updated successfully!')
        return redirect('post_detail', slug=post.slug)
    
    # Pre-populate tags as comma-separated string
    tags_str = ', '.join(post.tags) if isinstance(post.tags, list) else str(post.tags)
    
    context = {
        'post': post,
        'form_type': 'update',
        'tags_str': tags_str,
        'categories': Category.objects.order_by('name'),
        'tag_options': Tag.objects.order_by('name'),
        'selected_manual_tags': list(post.manual_tags.values_list('id', flat=True)),
        'selected_primary_category': post.primary_category_id,
    }
    return render(request, 'blog/post_form.html', context)


@login_required
def post_delete(request, slug):
    """Delete blog post"""
    post = get_object_or_404(Post, slug=slug)
    
    if post.author != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete this post.')
        return redirect('post_detail', slug=post.slug)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('post_list')
    
    context = {'post': post}
    return render(request, 'blog/post_confirm_delete.html', context)


def semantic_search(request):
    """
    AI Semantic Search using embeddings
    Route: /search/
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'blog/search_results.html', {
            'query': '',
            'results': [],
            'message': 'Please enter a search query.'
        })
    
    try:
        # Generate embedding for search query
        query_embedding = generate_embedding(query)
        
        if not query_embedding:
            return render(request, 'blog/search_results.html', {
                'query': query,
                'results': [],
                'message': 'Error generating search embedding. Please try again.'
            })
        
        # Get all posts with embeddings
        posts = Post.objects.filter(status='published').exclude(embedding__isnull=True).exclude(embedding=[])
        
        # Calculate similarity scores
        results = []
        for post in posts:
            if post.embedding and len(post.embedding) > 0:
                similarity = cosine_similarity(query_embedding, post.embedding)
                if similarity > 0.3:  # Threshold for relevance
                    results.append({
                        'post': post,
                        'similarity': similarity
                    })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Limit to top 20 results
        results = results[:20]
        
        return render(request, 'blog/search_results.html', {
            'query': query,
            'results': results,
            'message': f'Found {len(results)} relevant results.'
        })
    
    except Exception as e:
        return render(request, 'blog/search_results.html', {
            'query': query,
            'results': [],
            'message': f'Error performing search: {str(e)}'
        })


@require_http_methods(["POST"])
def ai_tags(request):
    """
    AI endpoint for generating tags and category
    Route: /ai-tags/
    Input: JSON with 'content' field
    Output: JSON with 'category' and 'tags'
    """
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Content is required'
            }, status=400)
        
        # Generate tags and category
        result = generate_tags_and_category(content)
        
        # Check for errors
        if 'error' in result:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to generate tags and category'),
                'category': '',
                'tags': []
            })
        
        return JsonResponse({
            'success': True,
            'category': result.get('category', ''),
            'tags': result.get('tags', [])
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["POST"])
def ai_seo(request):
    """
    AI endpoint for generating SEO metadata
    Route: /ai-seo/
    Input: JSON with 'title' and 'content' fields
    Output: JSON with SEO metadata
    """
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        
        if not title or not content:
            return JsonResponse({
                'success': False,
                'error': 'Title and content are required'
            }, status=400)
        
        # Generate SEO metadata
        result = generate_seo_metadata(title, content)
        
        # Check for errors
        if 'error' in result:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to generate SEO metadata'),
                'seo_title': title,
                'meta_description': '',
                'seo_keywords': [],
                'slug_suggestion': ''
            })
        
        return JsonResponse({
            'success': True,
            'seo_title': result.get('seo_title', ''),
            'meta_description': result.get('meta_description', ''),
            'seo_keywords': result.get('seo_keywords', []),
            'slug_suggestion': result.get('slug_suggestion', '')
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

