/**
 * SortMeOut Website - Main JavaScript
 * Handles navigation, animations, and interactive features
 */

(function () {
    'use strict';

    // ==========================================
    // DOM Elements
    // ==========================================

    const header = document.querySelector('.header');
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');
    const copyButtons = document.querySelectorAll('.copy-btn');
    const screenshotDots = document.querySelectorAll('.screenshot-dot');
    const screenshotsTrack = document.querySelector('.screenshots-track');

    // ==========================================
    // Navigation
    // ==========================================

    // Mobile menu toggle
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
            navToggle.setAttribute('aria-expanded', !isExpanded);
            navMenu.classList.toggle('active');
            document.body.style.overflow = !isExpanded ? 'hidden' : '';
        });

        // Close menu on link click
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                navToggle.setAttribute('aria-expanded', 'false');
                navMenu.classList.remove('active');
                document.body.style.overflow = '';
            });
        });

        // Close menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && navMenu.classList.contains('active')) {
                navToggle.setAttribute('aria-expanded', 'false');
                navMenu.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }

    // Header scroll effect
    let lastScrollY = window.scrollY;

    function updateHeader() {
        const scrollY = window.scrollY;

        if (scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        lastScrollY = scrollY;
    }

    window.addEventListener('scroll', updateHeader, { passive: true });
    updateHeader();

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                const headerHeight = header.offsetHeight;
                const targetPosition = target.getBoundingClientRect().top + window.scrollY - headerHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // ==========================================
    // Copy to Clipboard
    // ==========================================

    copyButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const textToCopy = button.dataset.copy;

            try {
                await navigator.clipboard.writeText(textToCopy);

                // Visual feedback
                button.classList.add('copied');
                button.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                        <path d="M13.333 4L6 11.333 2.667 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                `;

                // Reset after delay
                setTimeout(() => {
                    button.classList.remove('copied');
                    button.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                            <path d="M5 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V4a2 2 0 012-2z" stroke="currentColor" stroke-width="1.5"/>
                            <path d="M9 6h4a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V8a2 2 0 012-2z" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="1.5"/>
                        </svg>
                    `;
                }, 2000);
            } catch (err) {
                console.error('Failed to copy:', err);
            }
        });
    });

    // ==========================================
    // Screenshots Carousel
    // ==========================================

    if (screenshotDots.length && screenshotsTrack) {
        let currentIndex = 0;

        function goToSlide(index) {
            const screenshots = screenshotsTrack.querySelectorAll('.screenshot');
            const slideWidth = screenshots[0].offsetWidth + 24; // Including gap

            screenshotsTrack.scrollTo({
                left: slideWidth * index,
                behavior: 'smooth'
            });

            // Update dots
            screenshotDots.forEach((dot, i) => {
                dot.classList.toggle('active', i === index);
            });

            currentIndex = index;
        }

        screenshotDots.forEach((dot, index) => {
            dot.addEventListener('click', () => goToSlide(index));
        });

        // Auto-advance carousel
        let autoplayInterval = setInterval(() => {
            const nextIndex = (currentIndex + 1) % screenshotDots.length;
            goToSlide(nextIndex);
        }, 5000);

        // Pause on hover
        screenshotsTrack.addEventListener('mouseenter', () => {
            clearInterval(autoplayInterval);
        });

        screenshotsTrack.addEventListener('mouseleave', () => {
            autoplayInterval = setInterval(() => {
                const nextIndex = (currentIndex + 1) % screenshotDots.length;
                goToSlide(nextIndex);
            }, 5000);
        });

        // Sync dots with scroll
        screenshotsTrack.addEventListener('scroll', () => {
            const screenshots = screenshotsTrack.querySelectorAll('.screenshot');
            const slideWidth = screenshots[0].offsetWidth + 24;
            const newIndex = Math.round(screenshotsTrack.scrollLeft / slideWidth);

            if (newIndex !== currentIndex) {
                currentIndex = newIndex;
                screenshotDots.forEach((dot, i) => {
                    dot.classList.toggle('active', i === currentIndex);
                });
            }
        }, { passive: true });
    }

    // ==========================================
    // Demo Rule Builder
    // ==========================================

    const demoConditions = document.getElementById('demo-conditions');
    const demoActions = document.getElementById('demo-actions');
    const addConditionBtn = document.getElementById('demo-add-condition');
    const addActionBtn = document.getElementById('demo-add-action');

    function updatePreview() {
        const conditionEl = demoConditions?.querySelector('.condition');
        const actionEl = demoActions?.querySelector('.action');

        if (!conditionEl || !actionEl) return;

        const attr = conditionEl.querySelector('.condition-attr').value;
        const op = conditionEl.querySelector('.condition-op').value;
        const value = conditionEl.querySelector('.condition-value').value;
        const actionType = actionEl.querySelector('.action-type').value;
        const actionParam = actionEl.querySelector('.action-param').value;

        const previewText = document.querySelector('.preview-text');
        if (previewText) {
            const opText = {
                'equals': 'equal to',
                'contains': 'containing',
                'in_list': 'is one of'
            }[op] || op;

            const actionText = {
                'move': `moved to ${actionParam}`,
                'copy': `copied to ${actionParam}`,
                'rename': `renamed to ${actionParam}`,
                'tag': `tagged with ${actionParam}`,
                'trash': 'moved to Trash'
            }[actionType] || actionType;

            previewText.innerHTML = `
                When a file with ${attr} <strong>${opText} ${value}</strong>, it will be
                <strong>${actionText}</strong>
            `;
        }
    }

    if (demoConditions) {
        demoConditions.addEventListener('change', updatePreview);
        demoConditions.addEventListener('input', updatePreview);
    }

    if (demoActions) {
        demoActions.addEventListener('change', updatePreview);
        demoActions.addEventListener('input', updatePreview);
    }

    if (addConditionBtn) {
        addConditionBtn.addEventListener('click', () => {
            const newCondition = document.createElement('div');
            newCondition.className = 'condition';
            newCondition.innerHTML = `
                <select class="condition-attr" aria-label="Attribute">
                    <option value="extension">Extension</option>
                    <option value="name" selected>Name</option>
                    <option value="size">Size</option>
                    <option value="date">Date Modified</option>
                </select>
                <select class="condition-op" aria-label="Operator">
                    <option value="contains" selected>contains</option>
                    <option value="equals">is</option>
                    <option value="in_list">is one of</option>
                </select>
                <input type="text" class="condition-value" value="" aria-label="Value" placeholder="Enter value">
                <button class="condition-remove" aria-label="Remove condition">×</button>
            `;
            demoConditions.appendChild(newCondition);

            newCondition.querySelector('.condition-remove').addEventListener('click', () => {
                newCondition.remove();
                updatePreview();
            });
        });
    }

    if (addActionBtn) {
        addActionBtn.addEventListener('click', () => {
            const newAction = document.createElement('div');
            newAction.className = 'action';
            newAction.innerHTML = `
                <select class="action-type" aria-label="Action type">
                    <option value="tag" selected>Add tags</option>
                    <option value="move">Move to folder</option>
                    <option value="copy">Copy to folder</option>
                    <option value="rename">Rename</option>
                    <option value="trash">Move to Trash</option>
                </select>
                <input type="text" class="action-param" value="" aria-label="Parameter" placeholder="Enter value">
                <button class="action-remove" aria-label="Remove action">×</button>
            `;
            demoActions.appendChild(newAction);

            newAction.querySelector('.action-remove').addEventListener('click', () => {
                newAction.remove();
                updatePreview();
            });
        });
    }

    // Remove buttons for initial conditions/actions
    document.querySelectorAll('.condition-remove, .action-remove').forEach(btn => {
        btn.addEventListener('click', function () {
            this.closest('.condition, .action').remove();
            updatePreview();
        });
    });

    // ==========================================
    // Intersection Observer Animations
    // ==========================================

    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const animatedElements = document.querySelectorAll(
        '.feature-card, .step, .testimonial, .pricing-card'
    );

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    animatedElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
        observer.observe(el);
    });

    // ==========================================
    // Active Navigation Highlight
    // ==========================================

    const sections = document.querySelectorAll('section[id]');

    function highlightNav() {
        const scrollY = window.scrollY + header.offsetHeight + 100;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');
            const navLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);

            if (scrollY >= sectionTop && scrollY < sectionTop + sectionHeight) {
                navLinks.forEach(link => link.classList.remove('active'));
                if (navLink) navLink.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', highlightNav, { passive: true });

    // ==========================================
    // Download Button Analytics
    // ==========================================

    const downloadButtons = document.querySelectorAll('a[href*="download"], a[href*=".dmg"]');

    downloadButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Track download event (replace with your analytics)
            if (typeof gtag !== 'undefined') {
                gtag('event', 'download', {
                    'event_category': 'engagement',
                    'event_label': 'SortMeOut Download',
                    'value': 1
                });
            }

            console.log('Download tracked');
        });
    });

    // ==========================================
    // Keyboard Navigation Improvements
    // ==========================================

    // Add keyboard support for screenshot dots
    screenshotDots.forEach((dot, index) => {
        dot.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                dot.click();
            }

            if (e.key === 'ArrowRight') {
                const nextIndex = (index + 1) % screenshotDots.length;
                screenshotDots[nextIndex].focus();
                screenshotDots[nextIndex].click();
            }

            if (e.key === 'ArrowLeft') {
                const prevIndex = (index - 1 + screenshotDots.length) % screenshotDots.length;
                screenshotDots[prevIndex].focus();
                screenshotDots[prevIndex].click();
            }
        });
    });

    // ==========================================
    // Performance: Lazy Loading Enhancement
    // ==========================================

    if ('loading' in HTMLImageElement.prototype) {
        // Browser supports native lazy loading
        const lazyImages = document.querySelectorAll('img[loading="lazy"]');
        lazyImages.forEach(img => {
            if (img.dataset.src) {
                img.src = img.dataset.src;
            }
        });
    } else {
        // Fallback for browsers without native support
        const lazyImageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                    }
                    lazyImageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[loading="lazy"]').forEach(img => {
            lazyImageObserver.observe(img);
        });
    }

    // ==========================================
    // Console Easter Egg
    // ==========================================

    console.log(`
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║   🗂️  SortMeOut - File Automation          ║
    ║                                           ║
    ║   Proprietary • macOS Only               ║
    ║   sortmeout.saidborna.com                ║
    ║                                           ║
    ║   © 2026 Said Borna. All rights reserved. ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
    `);

})();


// ==========================================
// Stripe Checkout (outside IIFE — global)
// ==========================================

const SORTMEOUT_API = 'https://api.sortmeout.saidborna.com';

async function startCheckout() {
    const btn = document.querySelector('.pricing-card-featured .pricing-cta');
    const originalText = btn ? btn.textContent : '';

    try {
        if (btn) {
            btn.textContent = 'Loading...';
            btn.disabled = true;
        }

        const response = await fetch(`${SORTMEOUT_API}/api/checkout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });

        const data = await response.json();

        if (data.url) {
            window.location.href = data.url;
        } else {
            alert('Could not start checkout. Please try again.');
        }
    } catch (error) {
        console.error('Checkout error:', error);
        alert('Could not connect to payment server. Please try again later.');
    } finally {
        if (btn) {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }
}
