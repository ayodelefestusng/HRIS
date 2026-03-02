/**
 * Centralized Application JS
 * Handles global HTMX events, common UI initializations, and utilities.
 */

document.addEventListener('DOMContentLoaded', function() {
    // 1. Initialize Bootstrap Tooltips & Popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 2. Global Select2 Initialization (if available)
    initSelect2();

    // 3. HTMX Global Configurations
    document.body.addEventListener('htmx:afterOnLoad', function(evt) {
        // Re-initialize UI components after HTMX content swap
        initSelect2();
    });

    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error("HTMX Response Error:", evt.detail.xhr.status);
        // showToast("danger", "A server error occurred. Please try again.");
    });
});

/**
 * Initialize all Select2 elements on the page
 */
function initSelect2() {
    if (typeof $ !== 'undefined' && $.fn.select2) {
        $('.select2').each(function() {
            $(this).select2({
                theme: 'bootstrap-5',
                width: '100%',
                placeholder: $(this).data('placeholder') || 'Select an option'
            });
        });
    }
}

/**
 * HTMX CSRF Configuration
 */
document.body.addEventListener("htmx:configRequest", (e) => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        e.detail.headers["X-CSRFToken"] = csrfToken;
    }
});

/**
 * Utility: Copy text to clipboard
 */
function copyToClipboard(text, successMsg = "Copied to clipboard!") {
    navigator.clipboard.writeText(text).then(() => {
        alert(successMsg); 
    }, (err) => {
        console.error('Could not copy text: ', err);
    });
}

/**
 * Share Logic (Centralized)
 */
function openShareModal(jobId) {
    fetch(`/ats/generate-share/${jobId}/`)
        .then(response => response.json())
        .then(data => {
            const input = document.getElementById('shareUrlInput');
            const modalEl = document.getElementById('shareModal');
            if (input && modalEl) {
                input.value = data.share_url;
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            }
        })
        .catch(err => console.error('Error generating share link:', err));
}

// Attach event listeners for share buttons globally
document.addEventListener('click', function(e) {
    if (e.target.closest('.share-btn')) {
        const btn = e.target.closest('.share-btn');
        const jobId = btn.getAttribute('data-job-id');
        if (jobId) openShareModal(jobId);
    }
});
