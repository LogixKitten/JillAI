// JavaScript for Account Settings Page
// Function to update persona image based on selection
function updatePersonaImage() {
    const uiMode = document.getElementById("uiModeSelect").value;
    const personaSelect = document.getElementById("personaSelect");
    const personaIcon = document.getElementById("personaIcon");
    const selectedPersonaTitle = document.getElementById("selectedPersonaTitle");
    const selectedPersona = personaSelect.value;
    
    // Map of persona names to image URLs
    const personaImages = {
        'jill': 'static/img/personas/jill.png',
        'zee': 'static/img/personas/zee.png',
        'whiskers': 'static/img/personas/whiskers.png',
        'buddy': 'static/img/personas/buddy.png',
        'sean': 'static/img/personas/sean.png',
        'olivia': 'static/img/personas/olivia.png',
        'arlo': 'static/img/personas/arlo.png',
        'max': 'static/img/personas/max.png',
        'frank': 'static/img/personas/frank.png',
        'kai': 'static/img/personas/kai.png',
        'sophia': 'static/img/personas/sophia.png',
        'leo': 'static/img/personas/leo.png',
        'dante': 'static/img/personas/dante.png',
        'grace': 'static/img/personas/grace.png',
        'alex': 'static/img/personas/alex.png'
    };

    // Update the image source
    if (uiMode === 'Simple') {
        personaIcon.src = 'static/img/personas/generic.png';
    } else if (personaImages[selectedPersona]) {
        personaIcon.src = personaImages[selectedPersona];
    }

    // Update the selected persona title
    selectedPersonaTitle.innerText = selectedPersona.charAt(0).toUpperCase() + selectedPersona.slice(1);
}

// Function to show a toast notification
function showToast(message, type) {
    const toastBody = document.querySelector(".toast-body");
    const toastElement = document.querySelector(".toast");
    const toastHeader = document.querySelector(".toast-header strong");

    if (message && message.trim() !== "") {
        // Inject message content
        toastBody.innerText = message;

        // Set different styling based on the type (success or error)
        if (type === 'success') {
            toastElement.classList.remove('bg-danger');
            toastElement.classList.add('bg-success');
            toastHeader.innerText = "Success";
        } else if (type === 'error') {
            toastElement.classList.remove('bg-success');
            toastElement.classList.add('bg-danger');
            toastHeader.innerText = "Error";
        }

        // Make the toast visible if it was hidden
        toastElement.style.display = "block";

        // Trigger the toast to display
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    }
}

// Function to handle form submission for updating preferences
$(document).ready(function() {
    $("form").on("submit", function(event) {
        event.preventDefault(); // Prevent the default form submission

        // Check if newPassword and confirmNewPassword are identical
        const newPassword = $("#newPassword").val();
        const confirmNewPassword = $("#confirmNewPassword").val();

        if (newPassword && newPassword !== confirmNewPassword) {
            // Show error toast notification if passwords do not match
            showToast("New Password Must Match Confirmation.", 'error');
            return; // Stop form submission
        }

        // Extract form data
        const formData = {
            FirstName: $("#firstName").val(),
            LastName: $("#lastName").val(),
            email: $("#email").val(),
            currentPassword: $("#currentPassword").val(),
            newPassword: $("#newPassword").val(),
            ZipCode: $("#zipCode").val(),
            Gender: $("#gender").val(),
            UImode: $("#uiModeSelect").val(),
            CurrentPersona: $("#personaSelect").val()
        };

        // Remove empty fields to avoid unnecessary updates
        Object.keys(formData).forEach(key => {
            if (!formData[key]) {
                delete formData[key];
            }
        });

        // Make an AJAX POST request to update preferences
        $.ajax({
            url: "/update_preferences",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(formData),
            success: function(response) {
                // Show success toast notification
                showToast("Preferences updated successfully.", 'success');
            },
            error: function(xhr, status, error) {
                // Show error toast notification
                showToast("Failed to update preferences", 'error');
            }
        });
    });
});