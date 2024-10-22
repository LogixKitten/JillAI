// Store the firstName in sessionStorage when the user leaves the first name input field (blur event)
document.querySelector("input[name='firstName']").addEventListener('blur', function () {
    const firstName = this.value.trim(); // Trim spaces to avoid empty entries

    if (firstName) {
        sessionStorage.setItem('firstName', firstName);
        
        // Call the function to update all modals that reference firstName
        updateFirstNameInModals();
    }
});

// Function to dynamically update all modals with firstName
function updateFirstNameInModals() {
    const firstName = sessionStorage.getItem('firstName');
    
    if (firstName) {
        // Select all elements with the class "replace-firstName"
        const nameElements = document.querySelectorAll('.replace-firstName');
        nameElements.forEach(function (element) {
            element.textContent = firstName;
        });
    }
}

// Run this function as soon as the document is ready, in case the user reloads the page
document.addEventListener('DOMContentLoaded', function () {
    updateFirstNameInModals();
});
