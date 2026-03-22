/**
 * Mobile Shop Management System - Main JavaScript
 */

const swalWithBootstrapButtons = (typeof Swal !== 'undefined')
    ? Swal.mixin({
        customClass: {
            confirmButton: 'btn btn-success ms-2',
            cancelButton: 'btn btn-danger'
        },
        buttonsStyling: false
    })
    : null;

const swalToast = (typeof Swal !== 'undefined')
    ? Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3200,
        timerProgressBar: true
    })
    : null;

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Render server flash messages as professional toast notifications.
    const flashEl = document.getElementById('flash-messages');
    if (flashEl && flashEl.textContent) {
        try {
            const flashes = JSON.parse(flashEl.textContent);
            flashes.forEach(([category, message]) => {
                const iconMap = {
                    success: 'success',
                    info: 'info',
                    warning: 'warning',
                    danger: 'error',
                    error: 'error'
                };
                showNotification(message, iconMap[category] || 'info');
            });
        } catch (e) {
            console.warn('Failed to parse flash messages', e);
        }
    }
});

/**
 * Format currency
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

/**
 * CSRF helpers
 */
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function appendCsrfToken(form) {
    const token = getCsrfToken();
    if (!token || !form) return;
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = token;
    form.appendChild(input);
}

/**
 * Format date
 */
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(new Date(date));
}

/**
 * Show loading state on button
 */
function setButtonLoading(button, loading = true) {
    if (loading) {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || 'Submit';
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const normalizedType = (type === 'danger') ? 'error' : type;
    if (swalToast) {
        swalToast.fire({
            icon: normalizedType,
            title: message
        });
        return;
    }
    window.alert(message);
}

/**
 * Confirm action
 */
function confirmAction({
    title = 'Are you sure?',
    text = "You won't be able to revert this!",
    confirmText = 'Yes, continue',
    cancelText = 'Cancel',
    icon = 'warning'
} = {}) {
    if (!swalWithBootstrapButtons) {
        return Promise.resolve(window.confirm(`${title}\n\n${text}`));
    }
    return swalWithBootstrapButtons.fire({
        title,
        text,
        icon,
        showCancelButton: true,
        confirmButtonText: confirmText,
        cancelButtonText: cancelText,
        reverseButtons: true
    }).then((result) => result.isConfirmed);
}

/**
 * Debounce function
 */
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

/**
 * Fetch with error handling
 */
async function fetchWithErrorHandling(url, options = {}) {
    try {
        const token = getCsrfToken();
        if (token) {
            options.headers = options.headers || {};
            if (!options.headers['X-CSRFToken']) {
                options.headers['X-CSRFToken'] = token;
            }
        }
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        showNotification('An error occurred. Please try again.', 'danger');
        throw error;
    }
}

/**
 * Export table to CSV
 */
function exportTableToCSV(filename) {
    const csv = [];
    const rows = document.querySelectorAll('table tr');

    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');

        for (let j = 0; j < cols.length; j++) {
            row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
        }

        csv.push(row.join(','));
    }

    downloadCSV(csv.join('\n'), filename);
}

/**
 * Download CSV
 */
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], { type: 'text/csv' });
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(csvFile);
    downloadLink.download = filename;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

/**
 * Print element
 */
function printElement(elementId) {
    const printWindow = window.open('', '', 'height=600,width=800');
    const element = document.getElementById(elementId);

    printWindow.document.write('<html><head><title>Print</title>');
    printWindow.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(element.innerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();

    setTimeout(() => {
        printWindow.print();
    }, 250);
}

/**
 * Validate email
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate phone
 */
function validatePhone(phone) {
    const re = /^[\d\s\-\+\(\)]+$/;
    return re.test(phone) && phone.replace(/\D/g, '').length >= 10;
}

/**
 * Clear form
 */
function clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

/**
 * Get form data as object
 */
function getFormData(formId) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const data = {};

    for (let [key, value] of formData.entries()) {
        if (data[key]) {
            if (Array.isArray(data[key])) {
                data[key].push(value);
            } else {
                data[key] = [data[key], value];
            }
        } else {
            data[key] = value;
        }
    }

    return data;
}

/**
 * Add event listener to all elements with class
 */
function addEventListenerToClass(className, event, callback) {
    const elements = document.querySelectorAll('.' + className);
    elements.forEach(element => {
        element.addEventListener(event, callback);
    });
}

/**
 * Highlight search term in text
 */
function highlightSearchTerm(text, term) {
    if (!term) return text;
    const regex = new RegExp(`(${term})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

/**
 * Calculate percentage
 */
function calculatePercentage(value, total) {
    if (total === 0) return 0;
    return ((value / total) * 100).toFixed(2);
}

/**
 * Sort array of objects by property
 */
function sortByProperty(array, property, ascending = true) {
    return array.sort((a, b) => {
        if (ascending) {
            return a[property] > b[property] ? 1 : -1;
        } else {
            return a[property] < b[property] ? 1 : -1;
        }
    });
}

/**
 * Filter array by property value
 */
function filterByProperty(array, property, value) {
    return array.filter(item => item[property] === value);
}

/**
 * Group array by property
 */
function groupByProperty(array, property) {
    return array.reduce((groups, item) => {
        const key = item[property];
        if (!groups[key]) {
            groups[key] = [];
        }
        groups[key].push(item);
        return groups;
    }, {});
}
