// JavaScript for Account Settings Page

// Function to fill placeholder text and set selections based on current user data
function fillUserPlaceholders(currentUser) {
    if (currentUser.FirstName) {
        document.getElementById("firstName").placeholder = currentUser.FirstName;
    }
    if (currentUser.LastName) {
        document.getElementById("lastName").placeholder = currentUser.LastName;
    }
    if (currentUser.email) {
        document.getElementById("email").placeholder = currentUser.email;
    }
    if (currentUser.ZipCode) {
        document.getElementById("zipCode").placeholder = currentUser.ZipCode;
    }
    if (currentUser.Gender) {
        document.getElementById("gender").placeholder = currentUser.Gender;
    }
    
    if (currentUser.UImode) {
        document.getElementById("uiModeSelect").value = currentUser.UImode;
    }
    if (currentUser.CurrentPersona) {
        document.getElementById("personaSelect").value = currentUser.CurrentPersona;
        updatePersonaImage(); // Update the persona image based on the selection
    }
}

// Function to update persona image based on selection
function updatePersonaImage() {
    const uiMode = document.getElementById("uiModeSelect").value;
    const personaSelect = document.getElementById("personaSelect");
    const personaIcon = document.getElementById("personaIcon");
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
}

// Function to handle form submission for updating preferences
$(document).ready(function() {
    // Assume currentUser object is passed from server-side rendering or fetched by an AJAX call
    const currentUser = {
        FirstName: "{{ current_user.FirstName }}",
        LastName: "{{ current_user.LastName }}",
        email: "{{ current_user.email }}",
        ZipCode: "{{ current_user.ZipCode }}",
        UImode: "{{ current_user.UIMode }}",
        CurrentPersona: "{{ current_user.CurrentPersona }}",
        Gender: "{{ current_user.Gender }}"
    };

    // Fill in the placeholders and set selections based on the current user data
    fillUserPlaceholders(currentUser);

    $("form").on("submit", function(event) {
        // Check if newPassword and confirmNewPassword are identical
        const newPassword = $("#newPassword").val();
        const confirmNewPassword = $("#confirmNewPassword").val();

        if (newPassword && newPassword !== confirmNewPassword) {
            // Show error toast notification if passwords do not match
            $(".toast-body").text("New password and confirm password do not match.");
            $(".toast").toast({ delay: 3000 });
            $(".toast").toast("show");
            return; // Stop form submission
        }
        event.preventDefault(); // Prevent the default form submission

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
                $(".toast-body").text("Preferences updated successfully.");
                $(".toast").toast({ delay: 3000 });
                $(".toast").toast("show");
            },
            error: function(xhr, status, error) {
                // Show error toast notification
                $(".toast-body").text("Failed to update preferences. Please try again.");
                $(".toast").toast({ delay: 3000 });
                $(".toast").toast("show");
            }
        });
    });
});