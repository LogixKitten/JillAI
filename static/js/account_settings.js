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
    if (uiMode === 'simple') {
        personaIcon.src = 'static/img/personas/generic.png';
    } else if (personaImages[selectedPersona]) {
        personaIcon.src = personaImages[selectedPersona];
    }

    // Update the selected persona title
    selectedPersonaTitle.innerText = selectedPersona.charAt(0).toUpperCase() + selectedPersona.slice(1);
}

// Ensure the persona image is set correctly when the page loads
document.addEventListener("DOMContentLoaded", function() {
    updatePersonaImage(); // Call the function initially to set the correct persona image

    // Attach event listener to personaSelect to update the image on change
    const personaSelect = document.getElementById("personaSelect");
    personaSelect.addEventListener("change", updatePersonaImage);

    // Attach event listener to uiModeSelect to update the image on change
    const uiModeSelect = document.getElementById("uiModeSelect");
    uiModeSelect.addEventListener("change", updatePersonaImage);

    

    // Load countries into the select element
    fetch("static/json/countries_with_us.json")
      .then(response => response.json())
      .then(countries => {
        const countrySelect = document.getElementById("countrySelect");        
        for (const [code, name] of Object.entries(countries)) {
          const option = document.createElement("option");
          option.value = code;
          option.textContent = name;
          if (code === userCountry) { 
            option.selected = true;  // Set the selected attribute if the country matches the user's country
            console.log("Setting selected country:", name);
          }
          countrySelect.appendChild(option);
        }
      })
      .catch(error => console.error("Error loading countries:", error));
});

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
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
        toast.show();

        // Listen for the hidden event to reset display to "none"
        toastElement.addEventListener("hidden.bs.toast", function () {
            toastElement.style.display = "none";
        });
    }
}

$(document).ready(function() {
    $("#accountSettingsForm").on("submit", function(event) {
        event.preventDefault(); // Prevent default form submission
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        const formData = {
            firstName: document.getElementById("firstName").value,
            lastName: document.getElementById("lastName").value,
            email: document.getElementById("email").value,
            currentPassword: document.getElementById("currentPassword").value,
            newPassword: document.getElementById("newPassword").value,
            zipCode: document.getElementById("zipCode").value,
            country: document.getElementById("countrySelect").value,
            state: document.getElementById("state").value,
            city: document.getElementById("city").value,
            UImode: document.getElementById("uiModeSelect").value,
            CurrentPersona: document.getElementById("personaSelect").value
        };

        // Remove empty fields to avoid unnecessary updates
        Object.keys(formData).forEach(key => {
            if (!formData[key]) {
                delete formData[key];
            }
        });

        // Make AJAX POST request
        $.ajax({
            url: "/update_preferences",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(formData),
            success: function(response) {
                // Display success toast
                showToast(response.message, 'success');
            },
            error: function(xhr) {
                // Display error toast
                const errorMessage = xhr.responseJSON && xhr.responseJSON.message ? xhr.responseJSON.message : "Failed to update preferences. Please try again.";
                showToast(errorMessage, 'error');
            }
        });
    });
});
