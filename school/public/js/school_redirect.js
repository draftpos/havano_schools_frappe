(function() {
    function interceptSchoolManagement() {
        if (typeof frappe === 'undefined') return;

        // Find School Management sidebar link and override its click
        var links = document.querySelectorAll('.item-anchor');
        links.forEach(function(link) {
            var label = link.querySelector('.sidebar-item-label');
            if (label && label.textContent.trim() === 'School Management') {
                // Remove existing listeners by cloning
                var newLink = link.cloneNode(true);
                link.parentNode.replaceChild(newLink, link);
                newLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.location.href = '/assets/school/html/admin_school_management.html';
                });
            }
        });
    }

    // Run after sidebar is built
    $(document).ready(function() {
        // Try multiple times as sidebar loads async
        setTimeout(interceptSchoolManagement, 500);
        setTimeout(interceptSchoolManagement, 1000);
        setTimeout(interceptSchoolManagement, 2000);

        // Also run on route change
        if (typeof frappe !== 'undefined' && frappe.router) {
            frappe.router.on('change', function() {
                setTimeout(interceptSchoolManagement, 500);
            });
        }
    });
})();
