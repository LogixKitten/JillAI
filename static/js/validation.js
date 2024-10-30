document.addEventListener('DOMContentLoaded', function() {

  // Validate email on blur
  const emailInput = document.getElementById('email');
  emailInput.addEventListener('blur', function() {
    const email = emailInput.value.trim(); // Trim to remove extra spaces

    if (email) { // Only send request if the email is not empty
      // Send AJAX request to validate the email
      fetch('/validate_email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
          'email': email
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.isValid) {
          emailInput.classList.remove('is-invalid');
          emailInput.classList.add('is-valid');
        } else {
          emailInput.classList.remove('is-valid');
          emailInput.classList.add('is-invalid');
        }
      })
      .catch(error => console.error('Error:', error));
    }
  });

  // Validate username on blur
  const userNameInput = document.getElementById('userName');
  userNameInput.addEventListener('blur', function() {
    const userName = userNameInput.value.trim(); // Trim to remove extra spaces

    if (userName) { // Only send request if the username is not empty
      // Send AJAX request to validate the username
      fetch('/validate_username', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams({
          'userName': userName
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.isValid) {
          userNameInput.classList.remove('is-invalid');
          userNameInput.classList.add('is-valid');
        } else {
          userNameInput.classList.remove('is-valid');
          userNameInput.classList.add('is-invalid');
        }
      })
      .catch(error => console.error('Error:', error));
    }
  });  

  // Event listener for the "Next" button to confirm the country selection
  document.getElementById("confirmCountryCheck").addEventListener("click", () => {
    // Hide initial text and radio options
    document.querySelector(".modal-4-text-countryRadio").style.display = "none";
    document.querySelector(".location-choice").style.display = "none";
    
    // Show the modal footer
    document.getElementById("modal-4-footer").style.display = "flex";
    
    // Determine which form to show based on the selected country
    const selectedCountry = document.querySelector('input[name="countryRadio"]:checked').value;
    if (selectedCountry === "US") {
      document.querySelector(".modal-4-text-USA").style.display = "grid";
      document.getElementById("usaLocationForm").style.display = "grid";
      
      // Set Zip Code as a required field
      document.getElementById("zipCode").required = true;

      // Remove required from other fields
      document.getElementById("countrySelect").required = false;
      document.getElementById("state").required = false;
      document.getElementById("city").required = false;

    } else {
      document.querySelector(".modal-4-text-Other").style.display = "grid";
      document.getElementById("internationalLocationForm").style.display = "grid";
      
      // Set fields in international form as required
      document.getElementById("countrySelect").required = true;
      document.getElementById("state").required = true;
      document.getElementById("city").required = true;

      // Load countries into the select element
      fetch("static/json/countries.json")
        .then(response => response.json())
        .then(countries => {
          const countrySelect = document.getElementById("countrySelect");
          // Clear any previous options
          countrySelect.innerHTML = '<option value="" disabled selected>Choose your country...</option>';
          for (const [code, name] of Object.entries(countries)) {
            const option = document.createElement("option");
            option.value = code;
            option.textContent = name;
            countrySelect.appendChild(option);
          }
        })
        .catch(error => console.error("Error loading countries:", error));
    }
  });

  // Get the date input element
  const dateOfBirthInput = document.getElementById('dateOfBirth');
  
  // Calculate the date exactly 18 years ago at UTC+14
  const today = new Date();
  const utcMinus12Date = new Date(Date.UTC(today.getUTCFullYear() - 18, today.getUTCMonth(), today.getUTCDate()));
  
  // Adjust for UTC+14 by adding 14 hours
  utcMinus12Date.setUTCHours(utcMinus12Date.getUTCHours() + 14);
  
  // Format the date as YYYY-MM-DD
  const formattedDate = utcMinus12Date.getUTCFullYear() + '-' +
                        String(utcMinus12Date.getUTCMonth() + 1).padStart(2, '0') + '-' +
                        String(utcMinus12Date.getUTCDate()).padStart(2, '0');  
  
  // Set the max attribute and initial value
  dateOfBirthInput.max = formattedDate;
  dateOfBirthInput.value = formattedDate;

  // Event listener for country radio buttons
  document.querySelectorAll('input[name="countryRadio"]').forEach((radio) => {
    radio.addEventListener('change', () => {
      document.getElementById("confirmCountryCheck").style.display = "flex";
    });
  });  
});


// Validate password dynamically on input
const passwordInput = document.getElementById('passwordInput');
const passwordIcon = document.getElementById('passwordIcon');
const requirements = {
  minLength: document.getElementById('minLength'),
  uppercase: document.getElementById('uppercase'),
  lowercase: document.getElementById('lowercase'),
  number: document.getElementById('number'),
  specialChar: document.getElementById('specialChar')
};

// Update requirements dynamically as the user types
passwordInput.addEventListener('input', () => {
  const value = passwordInput.value;

  // Check length
  if (value.length >= 8) {
    requirements.minLength.classList.add('valid');
  } else {
    requirements.minLength.classList.remove('valid');
  }

  // Check uppercase letter
  if (/[A-Z]/.test(value)) {
    requirements.uppercase.classList.add('valid');
  } else {
    requirements.uppercase.classList.remove('valid');
  }

  // Check lowercase letter
  if (/[a-z]/.test(value)) {
    requirements.lowercase.classList.add('valid');
  } else {
    requirements.lowercase.classList.remove('valid');
  }

  // Check number
  if (/[0-9]/.test(value)) {
    requirements.number.classList.add('valid');
  } else {
    requirements.number.classList.remove('valid');
  }

  // Check special character
  if (/[^A-Za-z0-9]/.test(value)) {
    requirements.specialChar.classList.add('valid');
  } else {
    requirements.specialChar.classList.remove('valid');
  }
});

// Toggle password visibility and icon
function togglePassword() {
  const isPassword = passwordInput.getAttribute('type') === 'password';
  passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
  passwordIcon.src = isPassword ? 'static/img/icons/eye-password-view.svg' : 'static/img/icons/eye-password-hide.svg';
  passwordIcon.alt = isPassword ? 'Hide Password' : 'Show Password';
}

// Show and hide requirements box on focus/blur
function showRequirements() {
  document.getElementById('passwordRequirements').style.display = 'block';  
}

function hideRequirements() {
  document.getElementById('passwordRequirements').style.display = 'none';
  const isValidPassword = Object.values(requirements).every(req => req.classList.contains("valid"));
  const successMessage = document.getElementById('passwordSuccessMessage');  
  if (isValidPassword) {    
    passwordInput.classList.add("input-valid");
    togglePasswordBtn.style.top = '13%';
    successMessage.style.display = "grid";
  } else {
      passwordInput.classList.remove("input-valid");
      togglePasswordBtn.style.top = '20%';
      successMessage.style.display = "none";
  }
}

// Submit form data and create account
document.getElementById('submitFormButton').addEventListener('click', function() {
  const country_check = document.querySelector('input[name="countryRadio"]:checked').value;

  // Collect common form data
  const email = document.querySelector('input[name="email"]').value;
  const userName = document.querySelector('input[name="userName"]').value;
  const password = document.querySelector('input[name="password"]').value;
  const firstName = document.querySelector('input[name="firstName"]').value;
  const lastName = document.querySelector('input[name="lastName"]').value;
  const dateOfBirth = document.querySelector('input[name="dateOfBirth"]').value;
  const gender = document.querySelector('input[name="gender"]:checked').value;

  // Create data object to send to the Flask route
  const formData = {
    email: email,
    userName: userName,
    password: password,
    firstName: firstName,
    lastName: lastName,
    dateOfBirth: dateOfBirth,
    gender: gender
  };

  if (country_check === 'US') {
    const zipCode = document.querySelector('input[name="zipCode"]').value;
    formData.zipCode = zipCode;
  } else {
    const city = document.querySelector('input[name="city"]').value;
    const state = document.querySelector('input[name="state"]').value;
    const country = document.querySelector('select[name="country"]').value;
    formData.city = city;
    formData.state = state;
    formData.country = country;
  }

  // Log each key and its type in formData before sending the request
  for (const [key, value] of Object.entries(formData)) {
    console.log(`${key}:`, value, `(${typeof value})`);
  }

  // Send the data to the Flask route via POST request
  fetch('/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(formData)
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
        if (data.first_login) {
            sessionStorage.setItem('showFirstLoginModal', 'true');
        }
        
        // Redirect to the dashboard
        window.location.href = '/dashboard';
    } else {
      // Handle errors (if any)
      console.error('Error creating account:', data.message);
    }
  })
  .catch(error => {
    console.error('Error:', error);
  });
});