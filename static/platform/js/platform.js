/**
 * EduFlow SaaS - Platform Developer Control Plane JavaScript
 * Location: static/platform/js/platform.js
 */

document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss platform alerts
    const alerts = document.querySelectorAll('.platform-alert');
    alerts.forEach((alert) => {
        setTimeout(() => {
            alert.classList.add('opacity-0', 'transition-opacity', 'duration-300');
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

/**
 * Open or close the Onboard School Modal.
 * @param {boolean} open
 */
function toggleOnboardModal(open) {
    const modal = document.getElementById('onboard-modal');
    if (!modal) return;
    if (open) {
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}
