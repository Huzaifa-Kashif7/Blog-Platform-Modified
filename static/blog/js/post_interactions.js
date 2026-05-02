(function () {
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

    document.addEventListener('click', function (e) {
        const likeBtn = e.target.closest('.js-like-btn');
        if (likeBtn) {
            e.preventDefault();
            const url = likeBtn.dataset.url;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
                .then(res => res.json())
                .then(data => {
                    likeBtn.classList.toggle('btn-outline-primary', !data.liked);
                    likeBtn.classList.toggle('btn-primary', data.liked);
                    const counter = likeBtn.querySelector('.like-count');
                    if (counter) {
                        counter.textContent = data.likes;
                    }
                })
                .catch(() => {
                    likeBtn.disabled = false;
                });
        }

        const bookmarkBtn = e.target.closest('.js-bookmark-btn');
        if (bookmarkBtn) {
            e.preventDefault();
            const url = bookmarkBtn.dataset.url;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
                .then(res => res.json())
                .then(data => {
                    bookmarkBtn.classList.toggle('btn-outline-warning', !data.bookmarked);
                    bookmarkBtn.classList.toggle('btn-warning', data.bookmarked);
                    const countEl = bookmarkBtn.querySelector('.bookmark-count');
                    if (countEl) {
                        countEl.textContent = data.count;
                    }
                });
        }

        const deleteCommentBtn = e.target.closest('.js-delete-comment');
        if (deleteCommentBtn) {
            e.preventDefault();
            if (!confirm('Delete this comment?')) {
                return;
            }
            const url = deleteCommentBtn.dataset.url;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        const commentItem = document.getElementById('comment-' + data.comment_id);
                        if (commentItem) {
                            commentItem.remove();
                        }
                        const counter = document.getElementById('commentCount');
                        if (counter) {
                            counter.textContent = data.comment_count;
                        }
                        const commentList = document.getElementById('commentList');
                        if (commentList && commentList.querySelectorAll('li[id^="comment-"]').length === 0) {
                            commentList.innerHTML = '<li class="list-group-item">No comments yet.</li>';
                        }
                    }
                });
        }

        const shareBtn = e.target.closest('.js-share-btn');
        if (shareBtn) {
            e.preventDefault();
            const url = shareBtn.dataset.url;
            if (navigator.share) {
                navigator.share({
                    title: document.title,
                    url,
                });
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(url).then(() => {
                    shareBtn.textContent = 'Link Copied!';
                    setTimeout(() => { shareBtn.textContent = 'Copy Link'; }, 1500);
                });
            }
        }
    });

    const commentForm = document.getElementById('commentForm');
    if (commentForm) {
        commentForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const url = commentForm.action;
            const formData = new FormData(commentForm);
            fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: formData,
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        const list = document.getElementById('commentList');
                        // Remove 'No comments yet.' placeholder if present
                        const placeholder = list.querySelector('li:not([id])');
                        if (placeholder) {
                            placeholder.remove();
                        }
                        list.insertAdjacentHTML('beforeend', data.html);
                        commentForm.reset();
                        const counter = document.getElementById('commentCount');
                        if (counter) {
                            counter.textContent = data.comment_count;
                        }
                    }
                });
        });
    }

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const applyTheme = theme => {
            document.documentElement.setAttribute('data-theme', theme);
            themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
        };
        const saved = localStorage.getItem('theme') || document.documentElement.getAttribute('data-theme') || 'light';
        applyTheme(saved);
        themeToggle.addEventListener('click', () => {
            const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            localStorage.setItem('theme', next);
            applyTheme(next);
        });
    }
})();

