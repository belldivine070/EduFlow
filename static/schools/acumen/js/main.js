/**
 * EduFlow SaaS - Default School Theme JavaScript
 * Location: static/schools/default/js/main.js
 *
 * Micro-interactions, password visibility toggle, mobile sidebar drawer,
 * searchable multi-select dropdowns, file upload previews, and toast handlers.
 */

document.addEventListener('DOMContentLoaded', () => {
    initToastNotifications();
    initMultiSelectDropdowns();
    initFileUploadPreviews();
    initOutsideClickDropdowns();
});

/**
 * Auto-dismiss floating toast notifications with smooth fade-out.
 */
function initToastNotifications() {
    const toasts = document.querySelectorAll('.toast-item');
    toasts.forEach((toast) => {
        setTimeout(() => {
            toast.classList.add('opacity-0', 'transition-opacity', 'duration-300');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    });
}

/**
 * Toggle password input visibility between 'password' and 'text'.
 * @param {string} fieldId - ID of password input element
 * @param {HTMLElement} btn - Button element containing eye icons
 */
function togglePassword(fieldId, btn) {
    const input = document.getElementById(fieldId);
    if (!input) return;

    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';

    const iconEye = btn.querySelector('.icon-eye');
    const iconEyeOff = btn.querySelector('.icon-eye-off');

    if (iconEye && iconEyeOff) {
        iconEye.classList.toggle('hidden', isPassword);
        iconEyeOff.classList.toggle('hidden', !isPassword);
    }
}

/**
 * Toggle mobile responsive sidebar drawer and backdrop.
 */
function toggleSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar || !backdrop) return;

    const isHidden = sidebar.classList.contains('-translate-x-full');
    if (isHidden) {
        sidebar.classList.remove('-translate-x-full');
        backdrop.classList.remove('hidden');
        setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
    } else {
        sidebar.classList.add('-translate-x-full');
        backdrop.classList.add('opacity-0');
        setTimeout(() => backdrop.classList.add('hidden'), 300);
    }
}

/**
 * Interactive Searchable Multi-Select Dropdown for Subject & Class Assignments.
 * Looks for containers with [data-multiselect].
 */
function initMultiSelectDropdowns() {
    const containers = document.querySelectorAll('[data-multiselect]');
    containers.forEach((container) => {
        const trigger = container.querySelector('[data-ms-trigger]');
        const panel = container.querySelector('[data-ms-panel]');
        const searchInput = container.querySelector('[data-ms-search]');
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        const summary = container.querySelector('[data-ms-summary]');
        const placeholder = container.getAttribute('data-placeholder') || 'Select options...';

        if (!trigger || !panel) return;

        const updateSummary = () => {
            const selected = Array.from(checkboxes)
                .filter((cb) => cb.checked)
                .map((cb) => cb.getAttribute('data-label') || cb.value);

            if (!summary) return;
            if (selected.length === 0) {
                summary.textContent = placeholder;
                summary.classList.add('text-slate-400');
                summary.classList.remove('text-slate-800', 'font-semibold');
            } else if (selected.length <= 2) {
                summary.textContent = selected.join(', ');
                summary.classList.remove('text-slate-400');
                summary.classList.add('text-slate-800', 'font-semibold');
            } else {
                summary.textContent = `${selected.length} subjects selected (${selected.slice(0, 2).join(', ')} +${selected.length - 2})`;
                summary.classList.remove('text-slate-400');
                summary.classList.add('text-slate-800', 'font-semibold');
            }
        };

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            panel.classList.toggle('hidden');
            if (!panel.classList.contains('hidden') && searchInput) {
                searchInput.focus();
            }
        });

        panel.addEventListener('click', (e) => e.stopPropagation());

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                const q = searchInput.value.trim().toLowerCase();
                container.querySelectorAll('[data-ms-option]').forEach((opt) => {
                    const text = opt.textContent.toLowerCase();
                    opt.classList.toggle('hidden', q !== '' && !text.includes(q));
                });
            });
        }

        checkboxes.forEach((cb) => cb.addEventListener('change', updateSummary));
        updateSummary();
    });
}

/**
 * Show selected file name and size on file inputs with [data-file-preview].
 */
function initFileUploadPreviews() {
    document.querySelectorAll('input[type="file"][data-file-preview]').forEach((input) => {
        const targetId = input.getAttribute('data-file-preview');
        const targetEl = document.getElementById(targetId);
        if (!targetEl) return;

        input.addEventListener('change', () => {
            if (input.files && input.files.length > 0) {
                const file = input.files[0];
                const sizeKb = (file.size / 1024).toFixed(1);
                targetEl.textContent = `Selected: ${file.name} (${sizeKb} KB)`;
                targetEl.classList.remove('hidden');
            } else {
                targetEl.textContent = '';
                targetEl.classList.add('hidden');
            }
        });
    });
}

/**
 * Close open multi-select panels and school switcher when clicking outside.
 */
function initOutsideClickDropdowns() {
    document.addEventListener('click', () => {
        document.querySelectorAll('[data-ms-panel]').forEach((panel) => {
            panel.classList.add('hidden');
        });
        const schoolMenu = document.getElementById('school-menu');
        if (schoolMenu && !schoolMenu.classList.contains('hidden')) {
            schoolMenu.classList.add('hidden');
        }
    });
}
